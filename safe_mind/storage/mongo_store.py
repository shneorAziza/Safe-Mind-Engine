from datetime import UTC, date, datetime
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from safe_mind.alerts.engine import rebuild_daily_alert_state, score_dict_from_model
from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.storage.models import AppUser, DailySignalRecord, NextIntegrationMapping, StoredSignalIds


class MongoSignalStore:
    def __init__(self, uri: str | None, database: str) -> None:
        if not uri:
            raise RuntimeError("SAFE_MIND_MONGODB_URI is required when using the MongoDB signal store.")
        self.uri = uri
        self.database_name = database
        self._client = None
        self._initialized = False
        self._initialize_lock = Lock()

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._initialize_lock:
            if self._initialized:
                return
            self.ping()
            db = self._get_client()[self.database_name]
            db.daily_signal_scores.create_index(
                [("child_user_id", 1), ("day", 1)],
                unique=True,
            )
            db.daily_signal_scores.create_index([("child_user_id", 1), ("should_send_alert", 1)])
            db.message_events.create_index("event_id", unique=True)
            db.message_events.create_index([("child_user_id", 1), ("day", 1)])
            db.next_integration_mappings.create_index("child_user_id", unique=True)
            db.user_baselines.create_index("child_user_id", unique=True)
            db.app_users.create_index("child_user_id", unique=True)
            db.app_users.create_index("token_hash", unique=True)
            db.app_users.create_index([("parent_phone", 1), ("external_device_id", 1)], unique=True)
            db.app_login_challenges.create_index("id", unique=True)
            db.app_login_challenges.create_index("expires_at")
            self._initialized = True

    def ping(self) -> None:
        self._get_client().admin.command("ping")

    def save_signal_features(
        self,
        *,
        event_id: UUID,
        child_user_id: UUID,
        device_id: UUID,
        occurred_at: datetime,
        source_app: str | None,
        features: SignalFeatures,
        pipeline_version: str,
    ) -> StoredSignalIds:
        day = occurred_at.date()
        scores = score_dict_from_model(features.scores)
        collection = self._db().daily_signal_scores
        now = datetime.now(UTC)
        signal_id = str(uuid4())

        if not self._claim_message_event(
            event_id=event_id,
            signal_id=signal_id,
            child_user_id=child_user_id,
            device_id=device_id,
            day=day,
            occurred_at=occurred_at,
            source_app=source_app,
            pipeline_version=pipeline_version,
            created_at=now,
        ):
            existing_event = self._db().message_events.find_one(
                {"event_id": str(event_id)},
                {"id": 1, "daily_signal_score_id": 1},
            )
            if not existing_event:
                raise RuntimeError("Duplicate message event was detected but not found.")
            daily_score_id = existing_event.get("daily_signal_score_id")
            if not daily_score_id:
                daily_row = self._db().daily_signal_scores.find_one(
                    {"child_user_id": str(child_user_id), "day": day.isoformat()},
                    {"id": 1},
                )
                daily_score_id = daily_row.get("id") if daily_row else None
            if not daily_score_id:
                raise RuntimeError("Duplicate message event did not include a daily signal score id.")
            return StoredSignalIds(
                signal_id=str(existing_event["id"]),
                daily_score_id=str(daily_score_id),
            )

        daily_id = str(uuid4())
        collection.update_one(
            {"child_user_id": str(child_user_id), "day": day.isoformat()},
            _atomic_daily_average_update(
                daily_id=daily_id,
                child_user_id=child_user_id,
                day=day,
                scores=scores,
                now=now,
            ),
            upsert=True,
        )
        daily_record = collection.find_one(
            {"child_user_id": str(child_user_id), "day": day.isoformat()},
            {"id": 1},
        )
        if not daily_record or not daily_record.get("id"):
            raise RuntimeError("MongoDB did not return a daily signal score id.")
        daily_id = str(daily_record["id"])
        self._db().message_events.update_one(
            {"event_id": str(event_id)},
            {"$set": {"daily_signal_score_id": daily_id, "updated_at": now}},
        )
        return StoredSignalIds(signal_id=signal_id, daily_score_id=daily_id)

    def list_signal_records_for_child(self, child_user_id: UUID) -> list[DailySignalRecord]:
        rows = self._db().daily_signal_scores.find(
            {"child_user_id": str(child_user_id)},
            sort=[("day", 1)],
        )
        return [
            DailySignalRecord(
                id=str(row["id"]),
                child_user_id=UUID(row["child_user_id"]),
                day=_as_date(row["day"]),
                created_at=_as_datetime(row["created_at"]),
                updated_at=_as_datetime(row["updated_at"]),
                message_count=int(row["message_count"]),
                scores={key: float(value) for key, value in row["scores"].items()},
                baseline_day_count=int(row.get("baseline_day_count", 0)),
                is_baseline_day=bool(row.get("is_baseline_day", False)),
                is_flagged=bool(row.get("is_flagged", False)),
                should_send_alert=bool(row.get("should_send_alert", False)),
                deviations_in_window=int(row.get("deviations_in_window", 0)),
                alert_reason=row.get("alert_reason", "insufficient_baseline"),
            )
            for row in rows
        ]

    def list_child_user_ids(self) -> list[UUID]:
        rows = self._db().daily_signal_scores.aggregate(
            [
                {"$group": {"_id": "$child_user_id", "last_seen": {"$max": "$day"}}},
                {"$sort": {"last_seen": -1}},
            ]
        )
        return [UUID(row["_id"]) for row in rows]

    def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list[date]:
        rows = self._db().daily_signal_scores.find(
            {"child_user_id": str(child_user_id), "should_send_alert": True},
            {"day": 1},
            sort=[("day", 1)],
        )
        return [_as_date(row["day"]) for row in rows]

    def save_parent_alert_decision(self, decision: ParentAlertDecision) -> str:
        decision_id = str(uuid4())
        self._db().parent_alert_decisions.update_one(
            {
                "child_user_id": str(decision.child_user_id),
                "target_day": decision.target_day.isoformat(),
            },
            {
                "$set": {
                    "child_user_id": str(decision.child_user_id),
                    "target_day": decision.target_day.isoformat(),
                    "should_send_push": decision.should_send_push,
                    "reason": decision.reason,
                    "deviations_in_window": decision.deviations_in_window,
                    "gate_window_days": decision.gate_window_days,
                    "required_deviation_days": decision.required_deviation_days,
                    "message_count": decision.message_count,
                },
                "$setOnInsert": {
                    "id": decision_id,
                    "created_at": datetime.now(UTC),
                },
                "$unset": {"daily_score": "", "baseline_score": ""},
            },
            upsert=True,
        )
        stored = self._db().parent_alert_decisions.find_one(
            {
                "child_user_id": str(decision.child_user_id),
                "target_day": decision.target_day.isoformat(),
            },
            {"id": 1},
        )
        if not stored or not stored.get("id"):
            raise RuntimeError("MongoDB did not return a stored alert decision id.")
        return str(stored["id"])

    def delete_parent_alert_decisions_for_child(self, child_user_id: UUID) -> int:
        result = self._db().daily_signal_scores.update_many(
            {"child_user_id": str(child_user_id)},
            {"$set": {"should_send_alert": False}},
        )
        return int(result.modified_count)

    def count(self) -> int:
        return int(self._db().daily_signal_scores.count_documents({}))

    def rebuild_daily_state(self, child_user_id: UUID) -> None:
        self._rebuild_daily_state(child_user_id)

    def save_next_integration_mapping(
        self,
        *,
        child_user_id: UUID,
        device_id: UUID,
        uid: str,
        external_device_id: str,
    ) -> None:
        now = datetime.now(UTC)
        self._db().next_integration_mappings.update_one(
            {"child_user_id": str(child_user_id)},
            {
                "$set": {
                    "child_user_id": str(child_user_id),
                    "device_id": str(device_id),
                    "uid": uid,
                    "external_device_id": external_device_id,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def get_next_integration_mapping(
        self,
        child_user_id: UUID,
    ) -> NextIntegrationMapping | None:
        row = self._db().next_integration_mappings.find_one({"child_user_id": str(child_user_id)})
        if not row:
            return None
        return NextIntegrationMapping(
            child_user_id=UUID(row["child_user_id"]),
            device_id=UUID(row["device_id"]),
            uid=row["uid"],
            external_device_id=row["external_device_id"],
            created_at=_as_datetime(row["created_at"]),
            updated_at=_as_datetime(row["updated_at"]),
        )

    def create_login_challenge(
        self,
        *,
        challenge_id: str,
        child_user_id: UUID,
        device_id: UUID,
        external_device_id: str,
        name: str,
        parent_phone: str,
        code_hash: str,
        expires_at: datetime,
    ) -> None:
        now = datetime.now(UTC)
        self._db().app_login_challenges.insert_one(
            {
                "id": challenge_id,
                "child_user_id": str(child_user_id),
                "device_id": str(device_id),
                "external_device_id": external_device_id,
                "name": name,
                "parent_phone": parent_phone,
                "code_hash": code_hash,
                "expires_at": expires_at,
                "created_at": now,
                "consumed_at": None,
            }
        )

    def consume_login_challenge(
        self,
        *,
        challenge_id: str,
        parent_phone: str,
        code_hash: str,
        now: datetime,
    ) -> AppUser | None:
        row = self._db().app_login_challenges.find_one_and_update(
            {
                "id": challenge_id,
                "parent_phone": parent_phone,
                "code_hash": code_hash,
                "expires_at": {"$gt": now},
                "consumed_at": None,
            },
            {"$set": {"consumed_at": now}},
        )
        if not row:
            return None
        return AppUser(
            child_user_id=UUID(row["child_user_id"]),
            device_id=UUID(row["device_id"]),
            external_device_id=row["external_device_id"],
            name=row["name"],
            parent_phone=row["parent_phone"],
            token_hash="",
            created_at=now,
            updated_at=now,
        )

    def upsert_app_user(
        self,
        *,
        child_user_id: UUID,
        device_id: UUID,
        external_device_id: str,
        name: str,
        parent_phone: str,
        token_hash: str,
    ) -> AppUser:
        now = datetime.now(UTC)
        self._db().app_users.update_one(
            {"child_user_id": str(child_user_id)},
            {
                "$set": {
                    "child_user_id": str(child_user_id),
                    "device_id": str(device_id),
                    "external_device_id": external_device_id,
                    "name": name,
                    "parent_phone": parent_phone,
                    "token_hash": token_hash,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        user = self.get_app_user_by_child_user_id(child_user_id)
        if user is None:
            raise RuntimeError("MongoDB did not return a stored app user.")
        return user

    def get_app_user_by_token_hash(self, token_hash: str) -> AppUser | None:
        return _app_user_from_row(self._db().app_users.find_one({"token_hash": token_hash}))

    def get_app_user_by_child_user_id(self, child_user_id: UUID) -> AppUser | None:
        return _app_user_from_row(
            self._db().app_users.find_one({"child_user_id": str(child_user_id)})
        )

    def update_app_user_name(
        self,
        *,
        child_user_id: UUID,
        name: str,
    ) -> AppUser:
        self._db().app_users.update_one(
            {"child_user_id": str(child_user_id)},
            {"$set": {"name": name, "updated_at": datetime.now(UTC)}},
        )
        user = self.get_app_user_by_child_user_id(child_user_id)
        if user is None:
            raise RuntimeError("App user was not found.")
        return user

    def _db(self) -> Any:
        return self._get_client()[self.database_name]

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:
                raise RuntimeError(
                    "pymongo is required for MongoDB storage. Install project dependencies first."
                ) from exc
            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                retryWrites=True,
            )
        return self._client

    def _claim_message_event(
        self,
        *,
        event_id: UUID,
        signal_id: str,
        child_user_id: UUID,
        device_id: UUID,
        day: date,
        occurred_at: datetime,
        source_app: str | None,
        pipeline_version: str,
        created_at: datetime,
    ) -> bool:
        try:
            self._db().message_events.insert_one(
                {
                    "id": signal_id,
                    "event_id": str(event_id),
                    "child_user_id": str(child_user_id),
                    "device_id": str(device_id),
                    "day": day.isoformat(),
                    "occurred_at": occurred_at,
                    "source_app": source_app,
                    "pipeline_version": pipeline_version,
                    "created_at": created_at,
                    "updated_at": created_at,
                    "status": "received",
                }
            )
            return True
        except Exception as exc:
            if _is_duplicate_key_error(exc):
                return False
            raise

    def _rebuild_daily_state(self, child_user_id: UUID) -> None:
        records, baseline_scores, _baseline_score = rebuild_daily_alert_state(
            self.list_signal_records_for_child(child_user_id)
        )
        now = datetime.now(UTC)
        if baseline_scores is not None:
            baseline_records = records[:10]
            self._db().user_baselines.update_one(
                {"child_user_id": str(child_user_id)},
                {
                    "$set": {
                        "child_user_id": str(child_user_id),
                        "baseline_start_day": baseline_records[0].day.isoformat(),
                        "baseline_end_day": baseline_records[-1].day.isoformat(),
                        "baseline_day_count": len(baseline_records),
                        "scores": baseline_scores,
                        "is_final": True,
                        "updated_at": now,
                    },
                    "$unset": {"baseline_score": ""},
                    "$setOnInsert": {
                        "id": str(uuid4()),
                        "created_at": now,
                    },
                },
                upsert=True,
            )
        for record in records:
            self._db().daily_signal_scores.update_one(
                {"id": record.id},
                {
                    "$set": {
                        "baseline_day_count": record.baseline_day_count,
                        "is_baseline_day": record.is_baseline_day,
                        "is_flagged": record.is_flagged,
                        "should_send_alert": record.should_send_alert,
                        "deviations_in_window": record.deviations_in_window,
                        "alert_reason": record.alert_reason,
                        "updated_at": now,
                    },
                    "$unset": {
                        "baseline_scores": "",
                        "baseline_score": "",
                        "daily_score": "",
                        "delta": "",
                        "pipeline_version": "",
                        "score_totals": "",
                    },
                },
            )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(str(value))


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value)).date()


def _app_user_from_row(row: dict[str, Any] | None) -> AppUser | None:
    if not row:
        return None
    return AppUser(
        child_user_id=UUID(row["child_user_id"]),
        device_id=UUID(row["device_id"]),
        external_device_id=row["external_device_id"],
        name=row["name"],
        parent_phone=row["parent_phone"],
        token_hash=row["token_hash"],
        created_at=_as_datetime(row["created_at"]),
        updated_at=_as_datetime(row["updated_at"]),
    )


def _atomic_daily_average_update(
    *,
    daily_id: str,
    child_user_id: UUID,
    day: date,
    scores: dict[str, float],
    now: datetime,
) -> list[dict[str, Any]]:
    previous_count = {"$ifNull": ["$message_count", 0]}
    next_count = {"$add": [previous_count, 1]}
    averaged_scores = {
        key: {
            "$divide": [
                {
                    "$add": [
                        {
                            "$multiply": [
                                {"$ifNull": [f"$scores.{key}", 0.0]},
                                previous_count,
                            ]
                        },
                        value,
                    ]
                },
                next_count,
            ]
        }
        for key, value in scores.items()
    }
    return [
        {
            "$set": {
                "id": {"$ifNull": ["$id", daily_id]},
                "child_user_id": str(child_user_id),
                "day": day.isoformat(),
                "message_count": next_count,
                "scores": averaged_scores,
                "updated_at": now,
                "created_at": {"$ifNull": ["$created_at", now]},
                "baseline_day_count": {"$ifNull": ["$baseline_day_count", 0]},
                "is_baseline_day": {"$ifNull": ["$is_baseline_day", False]},
                "is_flagged": {"$ifNull": ["$is_flagged", False]},
                "should_send_alert": {"$ifNull": ["$should_send_alert", False]},
                "deviations_in_window": {"$ifNull": ["$deviations_in_window", 0]},
                "alert_reason": {"$ifNull": ["$alert_reason", "insufficient_baseline"]},
            }
        }
    ]


def _is_duplicate_key_error(exc: Exception) -> bool:
    try:
        from pymongo.errors import DuplicateKeyError
    except ImportError:
        return False
    return isinstance(exc, DuplicateKeyError)

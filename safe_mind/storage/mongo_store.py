from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from safe_mind.alerts.engine import rebuild_daily_alert_state, score_dict_from_model
from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.storage.models import DailySignalRecord


class MongoSignalStore:
    def __init__(self, uri: str | None, database: str) -> None:
        if not uri:
            raise RuntimeError("SAFE_MIND_MONGODB_URI is required when using the MongoDB signal store.")
        self.uri = uri
        self.database_name = database
        self._client = None

    def initialize(self) -> None:
        client = self._get_client()
        client.admin.command("ping")
        db = client[self.database_name]
        db.daily_signal_scores.create_index(
            [("child_user_id", 1), ("day", 1)],
            unique=True,
        )
        db.daily_signal_scores.create_index([("child_user_id", 1), ("should_send_alert", 1)])
        db.user_baselines.create_index("child_user_id", unique=True)

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
    ) -> str:
        del event_id, device_id, source_app, pipeline_version
        day = occurred_at.date()
        scores = score_dict_from_model(features.scores)
        collection = self._db().daily_signal_scores
        existing = collection.find_one({"child_user_id": str(child_user_id), "day": day.isoformat()})
        now = datetime.now(UTC)
        if existing:
            daily_id = existing["id"]
            previous_count = int(existing["message_count"])
            message_count = previous_count + 1
            previous_scores = existing["scores"]
            created_at = existing["created_at"]
        else:
            daily_id = str(uuid4())
            previous_count = 0
            message_count = 1
            previous_scores = {key: 0.0 for key in scores}
            created_at = now

        averaged = {
            key: ((float(previous_scores.get(key, 0.0)) * previous_count) + value) / message_count
            for key, value in scores.items()
        }
        collection.update_one(
            {"child_user_id": str(child_user_id), "day": day.isoformat()},
            {
                "$set": {
                    "child_user_id": str(child_user_id),
                    "day": day.isoformat(),
                    "message_count": message_count,
                    "scores": averaged,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "id": daily_id,
                    "created_at": created_at,
                    "baseline_day_count": 0,
                    "is_baseline_day": False,
                    "is_flagged": False,
                    "should_send_alert": False,
                    "deviations_in_window": 0,
                    "alert_reason": "insufficient_baseline",
                },
            },
            upsert=True,
        )
        self._rebuild_daily_state(child_user_id)
        return daily_id

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
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        return self._client

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

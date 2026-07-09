import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from safe_mind.alerts.engine import rebuild_daily_alert_state, score_dict_from_model
from pydantic import BaseModel

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.storage.models import AppUser, DailySignalRecord, NextIntegrationMapping, StoredSignalIds


class SignalVectorRecord(BaseModel):
    id: str
    event_id: UUID
    child_user_id: UUID
    device_id: UUID
    occurred_at: datetime
    source_app: str | None
    embedding_vector: list[float]
    features: SignalFeatures
    pipeline_version: str


class SignalRecord(BaseModel):
    id: str
    event_id: UUID
    child_user_id: UUID
    device_id: UUID
    occurred_at: datetime
    source_app: str | None
    features: SignalFeatures
    pipeline_version: str


class SQLiteVectorStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists signal_vectors (
                    id text primary key,
                    event_id text not null,
                    child_user_id text not null,
                    device_id text not null,
                    occurred_at text not null,
                    source_app text,
                    vector_json text not null,
                    embedding_model text not null,
                    embedding_dimensions integer not null,
                    features_json text not null,
                    pipeline_version text not null,
                    created_at text not null
                )
                """
            )
            connection.execute(
                "create index if not exists idx_signal_vectors_user_time "
                "on signal_vectors(child_user_id, occurred_at)"
            )
            connection.execute(
                """
                create table if not exists daily_signal_scores (
                    id text primary key,
                    child_user_id text not null,
                    day text not null,
                    message_count integer not null,
                    scores_json text not null,
                    baseline_day_count integer not null,
                    is_baseline_day integer not null,
                    is_flagged integer not null,
                    should_send_alert integer not null,
                    deviations_in_window integer not null,
                    alert_reason text not null,
                    created_at text not null,
                    updated_at text not null,
                    unique(child_user_id, day)
                )
                """
            )
            connection.execute(
                "create index if not exists idx_daily_signal_scores_user_day "
                "on daily_signal_scores(child_user_id, day)"
            )
            connection.execute(
                """
                create table if not exists user_baselines (
                    id text primary key,
                    child_user_id text not null,
                    baseline_start_day text not null,
                    baseline_end_day text not null,
                    baseline_day_count integer not null,
                    scores_json text not null,
                    is_final integer not null,
                    created_at text not null,
                    updated_at text not null,
                    unique(child_user_id)
                )
                """
            )
            connection.execute(
                """
                create table if not exists signal_feature_records (
                    id text primary key,
                    event_id text not null,
                    child_user_id text not null,
                    device_id text not null,
                    occurred_at text not null,
                    source_app text,
                    features_json text not null,
                    pipeline_version text not null,
                    created_at text not null,
                    unique(event_id)
                )
                """
            )
            connection.execute(
                "create index if not exists idx_signal_feature_records_user_time "
                "on signal_feature_records(child_user_id, occurred_at)"
            )
            connection.execute(
                """
                create table if not exists parent_alert_decisions (
                    id text primary key,
                    child_user_id text not null,
                    target_day text not null,
                    should_send_push integer not null,
                    reason text not null,
                    deviations_in_window integer not null,
                    gate_window_days integer not null,
                    required_deviation_days integer not null,
                    message_count integer not null,
                    created_at text not null,
                    unique(child_user_id, target_day)
                )
                """
            )
            connection.execute(
                "create index if not exists idx_parent_alert_decisions_user_day "
                "on parent_alert_decisions(child_user_id, target_day)"
            )
            connection.execute(
                """
                create table if not exists next_integration_mappings (
                    child_user_id text primary key,
                    device_id text not null,
                    uid text not null,
                    external_device_id text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists app_users (
                    child_user_id text primary key,
                    device_id text not null,
                    external_device_id text not null,
                    name text not null,
                    parent_phone text not null,
                    token_hash text not null,
                    created_at text not null,
                    updated_at text not null,
                    unique(parent_phone, external_device_id),
                    unique(token_hash)
                )
                """
            )
            connection.execute(
                "create index if not exists idx_app_users_token_hash on app_users(token_hash)"
            )
            connection.execute(
                """
                create table if not exists app_login_challenges (
                    id text primary key,
                    child_user_id text not null,
                    device_id text not null,
                    external_device_id text not null,
                    name text not null,
                    parent_phone text not null,
                    code_hash text not null,
                    expires_at text not null,
                    consumed_at text,
                    created_at text not null
                )
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("select 1").fetchone()

    def save_signal_vector(
        self,
        *,
        event_id: UUID,
        child_user_id: UUID,
        device_id: UUID,
        occurred_at: datetime,
        source_app: str | None,
        embedding: EmbeddingResult,
        features: SignalFeatures,
        pipeline_version: str,
    ) -> StoredSignalIds:
        vector_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                insert into signal_vectors (
                    id,
                    event_id,
                    child_user_id,
                    device_id,
                    occurred_at,
                    source_app,
                    vector_json,
                    embedding_model,
                    embedding_dimensions,
                    features_json,
                    pipeline_version,
                    created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vector_id,
                    str(event_id),
                    str(child_user_id),
                    str(device_id),
                    occurred_at.isoformat(),
                    source_app,
                    json.dumps(embedding.vector),
                    embedding.model,
                    embedding.dimensions,
                    features.model_dump_json(),
                    pipeline_version,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return vector_id

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
        day = occurred_at.date()
        scores = score_dict_from_model(features.scores)
        now = datetime.now(UTC)
        daily_id = str(uuid4())
        signal_id = str(uuid4())
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    insert into signal_feature_records (
                        id,
                        event_id,
                        child_user_id,
                        device_id,
                        occurred_at,
                        source_app,
                        features_json,
                        pipeline_version,
                        created_at
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal_id,
                        str(event_id),
                        str(child_user_id),
                        str(device_id),
                        occurred_at.isoformat(),
                        source_app,
                        features.model_dump_json(),
                        pipeline_version,
                        now.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError:
                row = connection.execute(
                    "select id from signal_feature_records where event_id = ?",
                    (str(event_id),),
                ).fetchone()
                if row:
                    daily_row = connection.execute(
                        """
                        select id from daily_signal_scores
                        where child_user_id = ? and day = ?
                        """,
                        (str(child_user_id), day.isoformat()),
                    ).fetchone()
                    if not daily_row:
                        raise RuntimeError(
                            "Duplicate signal feature record did not include a daily score."
                        )
                    return StoredSignalIds(signal_id=str(row[0]), daily_score_id=str(daily_row[0]))
                raise

            row = connection.execute(
                """
                select id, message_count, scores_json, created_at
                from daily_signal_scores
                where child_user_id = ? and day = ?
                """,
                (str(child_user_id), day.isoformat()),
            ).fetchone()
            if row:
                daily_id = row[0]
                previous_count = int(row[1])
                message_count = previous_count + 1
                previous_scores = json.loads(row[2])
                created_at = row[3]
            else:
                previous_count = 0
                message_count = 1
                previous_scores = {key: 0.0 for key in scores}
                created_at = now.isoformat()

            averaged = {
                key: ((float(previous_scores.get(key, 0.0)) * previous_count) + value) / message_count
                for key, value in scores.items()
            }
            connection.execute(
                """
                insert into daily_signal_scores (
                    id, child_user_id, day, message_count, scores_json,
                    baseline_day_count, is_baseline_day,
                    is_flagged, should_send_alert, deviations_in_window,
                    alert_reason, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(child_user_id, day) do update set
                    message_count = excluded.message_count,
                    scores_json = excluded.scores_json,
                    updated_at = excluded.updated_at
                """,
                (
                    daily_id,
                    str(child_user_id),
                    day.isoformat(),
                    message_count,
                    json.dumps(averaged),
                    0,
                    0,
                    0,
                    0,
                    0,
                    "insufficient_baseline",
                    created_at,
                    now.isoformat(),
                ),
            )
        return StoredSignalIds(signal_id=signal_id, daily_score_id=daily_id)

    def list_signal_records_for_child(self, child_user_id: UUID) -> list[DailySignalRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select
                    id,
                    child_user_id,
                    day,
                    message_count,
                    scores_json,
                    baseline_day_count,
                    is_baseline_day,
                    is_flagged,
                    should_send_alert,
                    deviations_in_window,
                    alert_reason,
                    created_at,
                    updated_at
                from daily_signal_scores
                where child_user_id = ?
                order by day asc
                """,
                (str(child_user_id),),
            ).fetchall()

        return [
            DailySignalRecord(
                id=row[0],
                child_user_id=UUID(row[1]),
                day=datetime.fromisoformat(row[2]).date(),
                message_count=int(row[3]),
                scores=json.loads(row[4]),
                baseline_day_count=int(row[5]),
                is_baseline_day=bool(row[6]),
                is_flagged=bool(row[7]),
                should_send_alert=bool(row[8]),
                deviations_in_window=int(row[9]),
                alert_reason=row[10],
                created_at=datetime.fromisoformat(row[11]),
                updated_at=datetime.fromisoformat(row[12]),
            )
            for row in rows
        ]

    def list_signal_vectors_for_child(self, child_user_id: UUID) -> list[SignalVectorRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select
                    id,
                    event_id,
                    child_user_id,
                    device_id,
                    occurred_at,
                    source_app,
                    vector_json,
                    features_json,
                    pipeline_version
                from signal_vectors
                where child_user_id = ?
                order by occurred_at asc
                """,
                (str(child_user_id),),
            ).fetchall()

        return [
            SignalVectorRecord(
                id=row[0],
                event_id=UUID(row[1]),
                child_user_id=UUID(row[2]),
                device_id=UUID(row[3]),
                occurred_at=datetime.fromisoformat(row[4]),
                source_app=row[5],
                embedding_vector=json.loads(row[6]),
                features=SignalFeatures.model_validate_json(row[7]),
                pipeline_version=row[8],
            )
            for row in rows
        ]

    def list_child_user_ids(self) -> list[UUID]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select child_user_id, max(day) as last_seen
                from daily_signal_scores
                group by child_user_id
                order by last_seen desc
                """
            ).fetchall()

        return [UUID(row[0]) for row in rows]

    def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list[date]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select day
                from daily_signal_scores
                where child_user_id = ? and should_send_alert = 1
                order by day asc
                """,
                (str(child_user_id),),
            ).fetchall()

        return [datetime.fromisoformat(row[0]).date() for row in rows]

    def save_parent_alert_decision(self, decision: ParentAlertDecision) -> str:
        decision_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                insert into parent_alert_decisions (
                    id,
                    child_user_id,
                    target_day,
                    should_send_push,
                    reason,
                    deviations_in_window,
                    gate_window_days,
                    required_deviation_days,
                    message_count,
                    created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(child_user_id, target_day) do update set
                    should_send_push = excluded.should_send_push,
                    reason = excluded.reason,
                    deviations_in_window = excluded.deviations_in_window,
                    gate_window_days = excluded.gate_window_days,
                    required_deviation_days = excluded.required_deviation_days,
                    message_count = excluded.message_count
                """,
                (
                    decision_id,
                    str(decision.child_user_id),
                    decision.target_day.isoformat(),
                    int(decision.should_send_push),
                    decision.reason,
                    decision.deviations_in_window,
                    decision.gate_window_days,
                    decision.required_deviation_days,
                    decision.message_count,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return decision_id

    def delete_parent_alert_decisions_for_child(self, child_user_id: UUID) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "delete from parent_alert_decisions where child_user_id = ?",
                (str(child_user_id),),
            )
        with self._connect() as connection:
            cursor = connection.execute(
                "update daily_signal_scores set should_send_alert = 0 where child_user_id = ?",
                (str(child_user_id),),
            )
        return int(cursor.rowcount or 0)

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("select count(*) from daily_signal_scores").fetchone()
        return int(row[0])

    def count_vectors(self) -> int:
        with self._connect() as connection:
            row = connection.execute("select count(*) from signal_vectors").fetchone()
        return int(row[0])

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
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "select created_at from next_integration_mappings where child_user_id = ?",
                (str(child_user_id),),
            ).fetchone()
            created_at = row[0] if row else now
            connection.execute(
                """
                insert into next_integration_mappings (
                    child_user_id, device_id, uid, external_device_id, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?)
                on conflict(child_user_id) do update set
                    device_id = excluded.device_id,
                    uid = excluded.uid,
                    external_device_id = excluded.external_device_id,
                    updated_at = excluded.updated_at
                """,
                (
                    str(child_user_id),
                    str(device_id),
                    uid,
                    external_device_id,
                    created_at,
                    now,
                ),
            )

    def get_next_integration_mapping(
        self,
        child_user_id: UUID,
    ) -> NextIntegrationMapping | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                select child_user_id, device_id, uid, external_device_id, created_at, updated_at
                from next_integration_mappings
                where child_user_id = ?
                """,
                (str(child_user_id),),
            ).fetchone()
        if not row:
            return None
        return NextIntegrationMapping(
            child_user_id=UUID(row[0]),
            device_id=UUID(row[1]),
            uid=row[2],
            external_device_id=row[3],
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
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
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                insert into app_login_challenges (
                    id, child_user_id, device_id, external_device_id, name,
                    parent_phone, code_hash, expires_at, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    challenge_id,
                    str(child_user_id),
                    str(device_id),
                    external_device_id,
                    name,
                    parent_phone,
                    code_hash,
                    expires_at.isoformat(),
                    now,
                ),
            )

    def consume_login_challenge(
        self,
        *,
        challenge_id: str,
        parent_phone: str,
        code_hash: str,
        now: datetime,
    ) -> AppUser | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                select child_user_id, device_id, external_device_id, name, parent_phone
                from app_login_challenges
                where id = ? and parent_phone = ? and code_hash = ?
                    and consumed_at is null and expires_at > ?
                """,
                (challenge_id, parent_phone, code_hash, now.isoformat()),
            ).fetchone()
            if not row:
                return None
            connection.execute(
                "update app_login_challenges set consumed_at = ? where id = ?",
                (now.isoformat(), challenge_id),
            )

        return AppUser(
            child_user_id=UUID(row[0]),
            device_id=UUID(row[1]),
            external_device_id=row[2],
            name=row[3],
            parent_phone=row[4],
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
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "select created_at from app_users where child_user_id = ?",
                (str(child_user_id),),
            ).fetchone()
            created_at = row[0] if row else now
            connection.execute(
                """
                insert into app_users (
                    child_user_id, device_id, external_device_id, name,
                    parent_phone, token_hash, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(child_user_id) do update set
                    device_id = excluded.device_id,
                    external_device_id = excluded.external_device_id,
                    name = excluded.name,
                    parent_phone = excluded.parent_phone,
                    token_hash = excluded.token_hash,
                    updated_at = excluded.updated_at
                """,
                (
                    str(child_user_id),
                    str(device_id),
                    external_device_id,
                    name,
                    parent_phone,
                    token_hash,
                    created_at,
                    now,
                ),
            )
        return self.get_app_user_by_child_user_id(child_user_id)  # type: ignore[return-value]

    def get_app_user_by_token_hash(self, token_hash: str) -> AppUser | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                select child_user_id, device_id, external_device_id, name,
                    parent_phone, token_hash, created_at, updated_at
                from app_users
                where token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
        return _app_user_from_row(row)

    def get_app_user_by_child_user_id(self, child_user_id: UUID) -> AppUser | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                select child_user_id, device_id, external_device_id, name,
                    parent_phone, token_hash, created_at, updated_at
                from app_users
                where child_user_id = ?
                """,
                (str(child_user_id),),
            ).fetchone()
        return _app_user_from_row(row)

    def update_app_user_name(
        self,
        *,
        child_user_id: UUID,
        name: str,
    ) -> AppUser:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "update app_users set name = ?, updated_at = ? where child_user_id = ?",
                (name, now, str(child_user_id)),
            )
        user = self.get_app_user_by_child_user_id(child_user_id)
        if user is None:
            raise RuntimeError("App user was not found.")
        return user

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _rebuild_daily_state(self, child_user_id: UUID) -> None:
        records, baseline_scores, _baseline_score = rebuild_daily_alert_state(
            self.list_signal_records_for_child(child_user_id)
        )
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            if baseline_scores is not None:
                baseline_records = records[:10]
                baseline_id = str(uuid4())
                existing = connection.execute(
                    "select id, created_at from user_baselines where child_user_id = ?",
                    (str(child_user_id),),
                ).fetchone()
                if existing:
                    baseline_id = existing[0]
                    created_at = existing[1]
                else:
                    created_at = now
                connection.execute(
                    """
                    insert into user_baselines (
                        id, child_user_id, baseline_start_day, baseline_end_day,
                        baseline_day_count, scores_json, is_final,
                        created_at, updated_at
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(child_user_id) do update set
                        baseline_start_day = excluded.baseline_start_day,
                        baseline_end_day = excluded.baseline_end_day,
                        baseline_day_count = excluded.baseline_day_count,
                        scores_json = excluded.scores_json,
                        is_final = excluded.is_final,
                        updated_at = excluded.updated_at
                    """,
                    (
                        baseline_id,
                        str(child_user_id),
                        baseline_records[0].day.isoformat(),
                        baseline_records[-1].day.isoformat(),
                        len(baseline_records),
                        json.dumps(baseline_scores),
                        1,
                        created_at,
                        now,
                    ),
                )

            for record in records:
                connection.execute(
                    """
                    update daily_signal_scores
                    set baseline_day_count = ?, is_baseline_day = ?,
                        is_flagged = ?, should_send_alert = ?, deviations_in_window = ?,
                        alert_reason = ?,
                        updated_at = ?
                    where id = ?
                    """,
                    (
                        record.baseline_day_count,
                        int(record.is_baseline_day),
                        int(record.is_flagged),
                        int(record.should_send_alert),
                        record.deviations_in_window,
                        record.alert_reason,
                        now,
                        record.id,
                    ),
                )


def _app_user_from_row(row: tuple | None) -> AppUser | None:
    if not row:
        return None
    return AppUser(
        child_user_id=UUID(row[0]),
        device_id=UUID(row[1]),
        external_device_id=row[2],
        name=row[3],
        parent_phone=row[4],
        token_hash=row[5],
        created_at=datetime.fromisoformat(row[6]),
        updated_at=datetime.fromisoformat(row[7]),
    )

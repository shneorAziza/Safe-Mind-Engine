import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.embeddings.models import EmbeddingResult


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
                create table if not exists parent_alert_decisions (
                    id text primary key,
                    child_user_id text not null,
                    target_day text not null,
                    should_send_push integer not null,
                    reason text not null,
                    daily_score real,
                    baseline_score real,
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
    ) -> str:
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
                select child_user_id, max(occurred_at) as last_seen
                from signal_vectors
                group by child_user_id
                order by last_seen desc
                """
            ).fetchall()

        return [UUID(row[0]) for row in rows]

    def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list[date]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select target_day
                from parent_alert_decisions
                where child_user_id = ? and should_send_push = 1
                order by target_day asc
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
                    daily_score,
                    baseline_score,
                    deviations_in_window,
                    gate_window_days,
                    required_deviation_days,
                    message_count,
                    created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(child_user_id, target_day) do update set
                    should_send_push = excluded.should_send_push,
                    reason = excluded.reason,
                    daily_score = excluded.daily_score,
                    baseline_score = excluded.baseline_score,
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
                    decision.daily_score,
                    decision.baseline_score,
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
        return int(cursor.rowcount or 0)

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("select count(*) from signal_vectors").fetchone()
        return int(row[0])

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

from typing import Protocol
from uuid import UUID
from datetime import date, datetime

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.core.config import settings
from safe_mind.storage.mongo_store import MongoSignalStore
from safe_mind.storage.models import DailySignalRecord
from safe_mind.storage.vector_store import SQLiteVectorStore


class SignalStore(Protocol):
    def initialize(self) -> None: ...

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
    ) -> str: ...

    def list_signal_records_for_child(self, child_user_id: UUID) -> list[DailySignalRecord]: ...

    def list_child_user_ids(self) -> list[UUID]: ...

    def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list[date]: ...

    def save_parent_alert_decision(self, decision: ParentAlertDecision) -> str: ...

    def delete_parent_alert_decisions_for_child(self, child_user_id: UUID) -> int: ...

    def count(self) -> int: ...


def get_signal_store() -> SignalStore:
    if settings.signal_store_provider == "mongodb":
        return MongoSignalStore(settings.mongodb_uri, settings.mongodb_database)
    return SQLiteVectorStore(settings.signal_db_path)

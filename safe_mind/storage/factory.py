from functools import lru_cache
from typing import Any, Protocol
from uuid import UUID
from datetime import date, datetime

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.core.config import settings
from safe_mind.storage.mongo_store import MongoSignalStore
from safe_mind.storage.models import AppUser, DailySignalRecord, NextIntegrationMapping, StoredSignalIds
from safe_mind.storage.vector_store import SQLiteVectorStore


class SignalStore(Protocol):
    def initialize(self) -> None: ...

    def ping(self) -> None: ...

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
        eval_message_text: str | None = None,
    ) -> StoredSignalIds: ...

    def list_signal_records_for_child(self, child_user_id: UUID) -> list[DailySignalRecord]: ...

    def list_child_user_ids(self) -> list[UUID]: ...

    def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list[date]: ...

    def save_parent_alert_decision(self, decision: ParentAlertDecision) -> str: ...

    def delete_parent_alert_decisions_for_child(self, child_user_id: UUID) -> int: ...

    def rebuild_daily_state(self, child_user_id: UUID) -> None: ...

    def save_next_integration_mapping(
        self,
        *,
        child_user_id: UUID,
        device_id: UUID,
        uid: str,
        external_device_id: str,
    ) -> None: ...

    def get_next_integration_mapping(
        self,
        child_user_id: UUID,
    ) -> NextIntegrationMapping | None: ...

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
    ) -> None: ...

    def consume_login_challenge(
        self,
        *,
        challenge_id: str,
        parent_phone: str,
        code_hash: str,
        now: datetime,
    ) -> AppUser | None: ...

    def upsert_app_user(
        self,
        *,
        child_user_id: UUID,
        device_id: UUID,
        external_device_id: str,
        name: str,
        parent_phone: str,
        token_hash: str,
    ) -> AppUser: ...

    def get_app_user_by_token_hash(self, token_hash: str) -> AppUser | None: ...

    def get_app_user_by_child_user_id(self, child_user_id: UUID) -> AppUser | None: ...

    def update_app_user_name(
        self,
        *,
        child_user_id: UUID,
        name: str,
    ) -> AppUser: ...

    def count(self) -> int: ...

    def create_eval_dataset_job(
        self,
        *,
        job_id: str,
        request_json: dict[str, Any],
        total_messages: int,
    ) -> None: ...

    def claim_eval_dataset_job(self, job_id: str) -> bool: ...

    def update_eval_dataset_job_progress(
        self,
        *,
        job_id: str,
        processed_messages: int,
        stage: str,
    ) -> None: ...

    def complete_eval_dataset_job(self, *, job_id: str, result_json: dict[str, Any]) -> None: ...

    def fail_eval_dataset_job(self, *, job_id: str, error: str) -> None: ...

    def get_eval_dataset_job(self, job_id: str) -> dict[str, Any] | None: ...


def get_signal_store() -> SignalStore:
    return _get_signal_store(
        settings.env,
        settings.signal_store_provider,
        settings.mongodb_uri,
        settings.mongodb_database,
        settings.signal_db_path,
    )


@lru_cache
def _get_signal_store(
    env: str,
    provider: str,
    mongodb_uri: str | None,
    mongodb_database: str,
    signal_db_path: str,
) -> SignalStore:
    if env.lower() == "production" and provider != "mongodb":
        raise RuntimeError("SAFE_MIND_SIGNAL_STORE_PROVIDER must be mongodb in production.")
    if provider == "mongodb":
        return MongoSignalStore(mongodb_uri, mongodb_database)
    return SQLiteVectorStore(signal_db_path)

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StoredSignal(BaseModel):
    stored: bool
    signal_id: str | None = None
    daily_score_id: str | None = None
    vector_id: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None


class StoredSignalIds(BaseModel):
    signal_id: str
    daily_score_id: str


class MessageScoreSnapshot(BaseModel):
    event_id: UUID
    occurred_at: datetime
    scores: dict[str, float]


class DailySignalRecord(BaseModel):
    id: str
    child_user_id: UUID
    day: date
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(ge=1)
    scores: dict[str, float]
    message_scores: list[MessageScoreSnapshot] = Field(default_factory=list)
    baseline_day_count: int = Field(default=0, ge=0)
    is_baseline_day: bool = False
    is_flagged: bool = False
    should_send_alert: bool = False
    alert_reason: str = "insufficient_baseline"
    deviations_in_window: int = Field(default=0, ge=0)


class UserBaseline(BaseModel):
    id: str
    child_user_id: UUID
    created_at: datetime
    updated_at: datetime
    baseline_start_day: date
    baseline_end_day: date
    baseline_day_count: int = Field(ge=1)
    scores: dict[str, float]
    is_final: bool = True


class NextIntegrationMapping(BaseModel):
    child_user_id: UUID
    device_id: UUID
    uid: str
    external_device_id: str
    created_at: datetime
    updated_at: datetime


class AppUser(BaseModel):
    child_user_id: UUID
    device_id: UUID
    external_device_id: str
    name: str
    parent_phone: str
    token_hash: str
    created_at: datetime
    updated_at: datetime

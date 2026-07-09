from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.privacy.models import PrivacySummary
from safe_mind.storage.models import StoredSignal


class IngestMessageRequest(BaseModel):
    event_id: UUID
    child_user_id: UUID
    device_id: UUID
    occurred_at: datetime
    source_type: Literal["notification", "share_intent", "accessibility", "manual"]
    source_app: str | None = Field(default=None, max_length=120)
    text: str = Field(min_length=1, max_length=10000)
    locale: str | None = Field(default=None, max_length=16)


class IngestMessageResponse(BaseModel):
    event_id: UUID
    status: Literal["accepted"]
    pipeline_stage: Literal["psychologically_analyzed"]
    privacy: PrivacySummary
    signal_features: SignalFeatures | None = None
    stored_signal: StoredSignal
    alert_decision: ParentAlertDecision | None = None


class StoredSignalAck(BaseModel):
    stored: bool
    signal_id: str | None = Field(default=None, alias="signalId")
    daily_score_id: str | None = Field(default=None, alias="dailyScoreId")

    model_config = {"populate_by_name": True}


class AppAcceptedMessage(BaseModel):
    message_id: str | None = Field(default=None, alias="messageId")
    event_id: UUID = Field(alias="eventId")
    status: Literal["accepted"]
    stored_signal: StoredSignalAck = Field(alias="storedSignal")

    model_config = {"populate_by_name": True}


class AppMessagesResponse(BaseModel):
    received: int
    accepted: int
    events: list[AppAcceptedMessage]

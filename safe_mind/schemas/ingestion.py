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
    text: str = Field(min_length=1, max_length=8000)
    locale: str | None = Field(default=None, max_length=16)


class IngestMessageResponse(BaseModel):
    event_id: UUID
    status: Literal["accepted"]
    pipeline_stage: Literal["psychologically_analyzed"]
    privacy: PrivacySummary
    signal_features: SignalFeatures | None = None
    stored_signal: StoredSignal
    alert_decision: ParentAlertDecision | None = None

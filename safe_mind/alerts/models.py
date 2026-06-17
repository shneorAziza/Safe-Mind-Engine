from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AlertDecisionReason = Literal[
    "no_signals",
    "insufficient_baseline",
    "below_gate",
    "cooldown_active",
    "gate_met",
]

TimelinePhase = Literal["pre_baseline", "baseline", "monitoring"]


class AlertPolicy(BaseModel):
    baseline_calibration_days: int = Field(default=10, ge=1)
    gate_window_days: int = Field(default=5, ge=1)
    required_deviation_days: int = Field(default=3, ge=1)
    min_baseline_days: int = Field(default=3, ge=1)
    deviation_threshold: float = Field(default=0.2, ge=0, le=1)
    cooldown_days: int = Field(default=5, ge=0)


class DailySignalScore(BaseModel):
    day: date
    average_score: float = Field(ge=0, le=1)
    message_count: int = Field(ge=1)


class DailyDeviation(BaseModel):
    day: date
    daily_score: float = Field(ge=0, le=1)
    baseline_score: float = Field(ge=0, le=1)
    baseline_day_count: int = Field(ge=0)
    delta: float
    is_deviation: bool


class ParentAlertDecision(BaseModel):
    child_user_id: UUID
    target_day: date
    should_send_push: bool
    reason: AlertDecisionReason
    daily_score: float | None = Field(default=None, ge=0, le=1)
    baseline_score: float | None = Field(default=None, ge=0, le=1)
    deviations_in_window: int = Field(default=0, ge=0)
    gate_window_days: int = Field(ge=1)
    required_deviation_days: int = Field(ge=1)
    message_count: int = Field(default=0, ge=0)


class AlertTimelineDay(BaseModel):
    day: date
    phase: TimelinePhase
    message_count: int = Field(default=0, ge=0)
    daily_score: float | None = Field(default=None, ge=0, le=1)
    baseline_score: float | None = Field(default=None, ge=0, le=1)
    baseline_day_count: int = Field(default=0, ge=0)
    delta: float | None = None
    is_deviation: bool = False
    deviations_in_window: int = Field(default=0, ge=0)
    should_send_push: bool = False
    reason: AlertDecisionReason

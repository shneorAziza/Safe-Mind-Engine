from typing import Literal

from pydantic import BaseModel, Field

PiiType = Literal["EMAIL", "PHONE", "URL", "ID_NUMBER", "ADDRESS"]
PrivacyRiskLevel = Literal["low", "medium", "high"]


class RedactionResult(BaseModel):
    redacted_text: str
    pii_detected: bool
    pii_types: list[PiiType] = Field(default_factory=list)
    redaction_count: int = 0
    risk_level: PrivacyRiskLevel = "low"


class PrivacySummary(BaseModel):
    pii_detected: bool
    pii_types: list[PiiType] = Field(default_factory=list)
    redaction_count: int
    risk_level: PrivacyRiskLevel


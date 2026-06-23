from typing import Literal

from pydantic import BaseModel, Field, model_validator

RiskLevel = Literal["none", "low", "medium", "high", "urgent"]
AnalyzerProvider = Literal["heuristic", "openai"]


class PsychologicalScores(BaseModel):
    positive_emotion: int = Field(default=5, ge=1, le=10)
    negative_emotion: int = Field(default=1, ge=1, le=10)
    loneliness: int = Field(default=1, ge=1, le=10)
    anxiety_stress: int = Field(default=1, ge=1, le=10)
    hopelessness: int = Field(default=1, ge=1, le=10)
    self_worth_low: int = Field(default=1, ge=1, le=10)
    risk: int = Field(default=1, ge=1, le=10)


class SignalFeatures(BaseModel):
    should_store: bool
    signal_strength: float = Field(default=0, ge=0, le=1)
    risk_level: RiskLevel
    scores: PsychologicalScores = Field(default_factory=PsychologicalScores)
    confidence: float = Field(ge=0, le=1)
    provider: AnalyzerProvider

    @model_validator(mode="after")
    def normalize_storage_decision(self) -> "SignalFeatures":
        self.should_store = True
        high_signal = max(
            self.scores.negative_emotion,
            self.scores.loneliness,
            self.scores.anxiety_stress,
            self.scores.hopelessness,
            self.scores.self_worth_low,
            self.scores.risk,
        )
        self.signal_strength = max(self.signal_strength, high_signal / 10)

        if self.risk_level == "urgent":
            self.should_store = True
            self.signal_strength = max(self.signal_strength, 0.9)
            self.confidence = max(self.confidence, 0.9)
            self.scores.risk = max(self.scores.risk, 9)

        return self


class PsychologicalAnalysisResult(BaseModel):
    features: SignalFeatures
    summary_for_embedding: str | None = Field(default=None, max_length=500)

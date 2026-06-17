from typing import Literal

from pydantic import BaseModel, Field, model_validator

RiskLevel = Literal["none", "low", "medium", "high", "urgent"]
AnalyzerProvider = Literal["heuristic", "openai"]


class EmotionScores(BaseModel):
    anxiety: float = Field(default=0, ge=0, le=1)
    sadness: float = Field(default=0, ge=0, le=1)
    anger: float = Field(default=0, ge=0, le=1)
    loneliness: float = Field(default=0, ge=0, le=1)
    shame: float = Field(default=0, ge=0, le=1)
    hopelessness: float = Field(default=0, ge=0, le=1)


class CbtPatternScores(BaseModel):
    catastrophizing: float = Field(default=0, ge=0, le=1)
    all_or_nothing: float = Field(default=0, ge=0, le=1)
    mind_reading: float = Field(default=0, ge=0, le=1)
    overgeneralization: float = Field(default=0, ge=0, le=1)
    self_blame: float = Field(default=0, ge=0, le=1)
    avoidance: float = Field(default=0, ge=0, le=1)


class ThemeScores(BaseModel):
    school: float = Field(default=0, ge=0, le=1)
    friends: float = Field(default=0, ge=0, le=1)
    parents: float = Field(default=0, ge=0, le=1)
    ai_dependency: float = Field(default=0, ge=0, le=1)
    academic_pressure: float = Field(default=0, ge=0, le=1)
    social_rejection: float = Field(default=0, ge=0, le=1)
    bullying: float = Field(default=0, ge=0, le=1)


class ProtectiveSignalScores(BaseModel):
    seeking_help: float = Field(default=0, ge=0, le=1)
    future_orientation: float = Field(default=0, ge=0, le=1)
    trusted_adult: float = Field(default=0, ge=0, le=1)
    problem_solving: float = Field(default=0, ge=0, le=1)
    social_support: float = Field(default=0, ge=0, le=1)


class SignalFeatures(BaseModel):
    should_store: bool
    signal_strength: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    emotion_scores: EmotionScores = Field(default_factory=EmotionScores)
    cbt_pattern_scores: CbtPatternScores = Field(default_factory=CbtPatternScores)
    theme_scores: ThemeScores = Field(default_factory=ThemeScores)
    protective_signal_scores: ProtectiveSignalScores = Field(default_factory=ProtectiveSignalScores)
    confidence: float = Field(ge=0, le=1)
    provider: AnalyzerProvider

    @model_validator(mode="after")
    def normalize_storage_decision(self) -> "SignalFeatures":
        if self.risk_level == "urgent":
            self.should_store = True
            self.signal_strength = max(self.signal_strength, 0.9)
            self.confidence = max(self.confidence, 0.9)

        if not self.should_store:
            self.signal_strength = min(self.signal_strength, 0.4)

        return self


class PsychologicalAnalysisResult(BaseModel):
    features: SignalFeatures
    summary_for_embedding: str = Field(min_length=1, max_length=500)

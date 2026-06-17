import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EmotionCategory = Literal[
    "distress",
    "anxiety",
    "loneliness",
    "anger",
    "self_worth",
    "hopelessness",
    "safety_risk",
]
RiskHint = Literal["none", "possible", "urgent"]
EmotionalFilterProvider = Literal["heuristic", "openai"]


class EmotionalFilterResult(BaseModel):
    is_emotionally_relevant: bool
    confidence: float = Field(ge=0, le=1)
    categories: list[EmotionCategory] = Field(default_factory=list)
    risk_hint: RiskHint = "none"
    provider: EmotionalFilterProvider = "heuristic"

    @model_validator(mode="after")
    def normalize_consistency(self) -> "EmotionalFilterResult":
        if self.risk_hint == "urgent":
            self.is_emotionally_relevant = True
            self.confidence = max(self.confidence, 0.9)
            if "safety_risk" not in self.categories:
                self.categories.append("safety_risk")

        if self.risk_hint == "possible":
            self.is_emotionally_relevant = True
            self.confidence = max(self.confidence, 0.55)

        if self.categories:
            self.is_emotionally_relevant = True

        if not self.is_emotionally_relevant:
            self.categories = []
            self.risk_hint = "none"
            self.confidence = min(self.confidence, 0.4)

        self.categories = list(dict.fromkeys(self.categories))
        self.confidence = round(self.confidence, 2)
        return self


@dataclass(frozen=True)
class KeywordRule:
    category: EmotionCategory
    weight: float
    patterns: tuple[re.Pattern[str], ...]


KEYWORD_RULES: tuple[KeywordRule, ...] = (
    KeywordRule(
        category="distress",
        weight=0.55,
        patterns=(
            re.compile(r"\b(overwhelmed|stressed|panic|crying|miserable|upset)\b", re.I),
            re.compile(
                r"(\u05de\u05d5\u05e6\u05e3|\u05dc\u05d7\u05d5\u05e5|\u05dc\u05d7\u05e5|"
                r"\u05d1\u05d5\u05db\u05d4|\u05e8\u05e2 \u05dc\u05d9)"
            ),
        ),
    ),
    KeywordRule(
        category="anxiety",
        weight=0.6,
        patterns=(
            re.compile(r"\b(anxious|anxiety|scared|afraid|worried|terrified)\b", re.I),
            re.compile(
                r"(\u05d7\u05e8\u05d3\u05d4|\u05d7\u05e8\u05d3|\u05e4\u05d7\u05d3|"
                r"\u05de\u05e4\u05d7\u05d3|\u05d3\u05d5\u05d0\u05d2)"
            ),
        ),
    ),
    KeywordRule(
        category="loneliness",
        weight=0.55,
        patterns=(
            re.compile(r"\b(alone|lonely|ignored|left out|no friends)\b", re.I),
            re.compile(
                r"(\u05dc\u05d1\u05d3|\u05d1\u05d5\u05d3\u05d3|\u05de\u05ea\u05e2\u05dc\u05de\u05d9\u05dd|"
                r"\u05d0\u05d9\u05df \u05dc\u05d9 \u05d7\u05d1\u05e8\u05d9\u05dd)"
            ),
        ),
    ),
    KeywordRule(
        category="anger",
        weight=0.45,
        patterns=(
            re.compile(r"\b(angry|furious|hate everyone|rage)\b", re.I),
            re.compile(r"(\u05db\u05d5\u05e2\u05e1|\u05e2\u05e6\u05d1\u05e0\u05d9|\u05e9\u05d5\u05e0\u05d0)"),
        ),
    ),
    KeywordRule(
        category="self_worth",
        weight=0.65,
        patterns=(
            re.compile(r"\b(worthless|failure|not good enough|everyone hates me)\b", re.I),
            re.compile(
                r"(\u05dc\u05d0 \u05e9\u05d5\u05d5\u05d4|\u05db\u05d9\u05e9\u05dc\u05d5\u05df|"
                r"\u05d0\u05e3 \u05d0\u05d7\u05d3 \u05dc\u05d0 \u05d0\u05d5\u05d4\u05d1 \u05d0\u05d5\u05ea\u05d9)"
            ),
        ),
    ),
    KeywordRule(
        category="hopelessness",
        weight=0.7,
        patterns=(
            re.compile(r"\b(no point|nothing matters|can't go on|give up)\b", re.I),
            re.compile(
                r"(\u05d0\u05d9\u05df \u05d8\u05e2\u05dd|\u05dc\u05d0 \u05de\u05e9\u05e0\u05d4|"
                r"\u05dc\u05d0 \u05d9\u05db\u05d5\u05dc \u05d9\u05d5\u05ea\u05e8|\u05de\u05d5\u05d5\u05ea\u05e8)"
            ),
        ),
    ),
    KeywordRule(
        category="safety_risk",
        weight=1.0,
        patterns=(
            re.compile(r"\b(kill myself|hurt myself|end my life|suicide|self harm)\b", re.I),
            re.compile(
                r"(\u05dc\u05d4\u05ea\u05d0\u05d1\u05d3|\u05dc\u05e4\u05d2\u05d5\u05e2 \u05d1\u05e2\u05e6\u05de\u05d9|"
                r"\u05dc\u05d4\u05e8\u05d5\u05d2 \u05d0\u05ea \u05e2\u05e6\u05de\u05d9|"
                r"\u05dc\u05d0 \u05e8\u05d5\u05e6\u05d4 \u05dc\u05d7\u05d9\u05d5\u05ea)"
            ),
        ),
    ),
)


def filter_emotional_relevance(text: str) -> EmotionalFilterResult:
    categories: list[EmotionCategory] = []
    score = 0.0

    for rule in KEYWORD_RULES:
        if any(pattern.search(text) for pattern in rule.patterns):
            categories.append(rule.category)
            score += rule.weight

    unique_categories = list(dict.fromkeys(categories))
    confidence = min(score, 0.98)

    if "safety_risk" in unique_categories:
        risk_hint: RiskHint = "urgent"
        confidence = 0.98
    elif {"hopelessness", "self_worth"} & set(unique_categories):
        risk_hint = "possible"
    else:
        risk_hint = "none"

    return EmotionalFilterResult(
        is_emotionally_relevant=confidence >= 0.45,
        confidence=round(confidence, 2),
        categories=unique_categories,
        risk_hint=risk_hint,
        provider="heuristic",
    )

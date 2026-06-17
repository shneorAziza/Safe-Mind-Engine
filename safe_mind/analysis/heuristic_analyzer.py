from safe_mind.analysis.models import (
    CbtPatternScores,
    EmotionScores,
    PsychologicalAnalysisResult,
    ProtectiveSignalScores,
    SignalFeatures,
    ThemeScores,
)
from safe_mind.signals.emotional_filter import EmotionalFilterResult


def analyze_with_heuristics(
    text: str,
    emotional_filter: EmotionalFilterResult,
) -> PsychologicalAnalysisResult:
    emotion_scores = EmotionScores(
        anxiety=0.75 if "anxiety" in emotional_filter.categories else 0,
        anger=0.75 if "anger" in emotional_filter.categories else 0,
        loneliness=0.75 if "loneliness" in emotional_filter.categories else 0,
        shame=0.65 if "self_worth" in emotional_filter.categories else 0,
        hopelessness=0.85 if "hopelessness" in emotional_filter.categories else 0,
        sadness=0.6 if "distress" in emotional_filter.categories else 0,
    )
    risk_level = "urgent" if emotional_filter.risk_hint == "urgent" else "none"
    if emotional_filter.risk_hint == "possible":
        risk_level = "medium"

    signal_strength = max(
        emotional_filter.confidence,
        emotion_scores.anxiety,
        emotion_scores.anger,
        emotion_scores.loneliness,
        emotion_scores.shame,
        emotion_scores.hopelessness,
        emotion_scores.sadness,
    )

    features = SignalFeatures(
        should_store=emotional_filter.is_emotionally_relevant,
        signal_strength=signal_strength,
        risk_level=risk_level,
        emotion_scores=emotion_scores,
        cbt_pattern_scores=CbtPatternScores(),
        theme_scores=_theme_scores(text),
        protective_signal_scores=_protective_scores(text),
        confidence=emotional_filter.confidence,
        provider="heuristic",
    )

    return PsychologicalAnalysisResult(
        features=features,
        summary_for_embedding="A privacy-redacted emotional signal from a teen AI conversation.",
    )


def _theme_scores(text: str) -> ThemeScores:
    return ThemeScores(
        school=0.8 if any(word in text for word in ("school", "בית ספר", "כיתה", "מבחן")) else 0,
        friends=0.8 if any(word in text for word in ("friend", "friends", "חבר", "חברים")) else 0,
        parents=0.8 if any(word in text for word in ("parent", "parents", "הורים", "אמא", "אבא")) else 0,
        academic_pressure=0.8 if any(word in text for word in ("test", "exam", "מבחן")) else 0,
        social_rejection=0.8 if any(word in text for word in ("ignored", "מתעלמים", "צוחקים")) else 0,
        bullying=0.8 if any(word in text for word in ("bully", "bullying", "צוחקים", "מציקים")) else 0,
    )


def _protective_scores(text: str) -> ProtectiveSignalScores:
    return ProtectiveSignalScores(
        seeking_help=0.8 if any(word in text for word in ("help", "עזרה", "תעזור")) else 0,
        trusted_adult=0.7 if any(word in text for word in ("teacher", "parent", "מורה", "הורים")) else 0,
        problem_solving=0.6 if any(word in text for word in ("how", "איך")) else 0,
    )

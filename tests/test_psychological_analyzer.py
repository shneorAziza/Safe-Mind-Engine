from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.openai_analyzer import OpenAIPsychologicalAnalyzer
from safe_mind.signals.emotional_filter import EmotionalFilterResult


def test_heuristic_analyzer_returns_features_and_temporary_summary() -> None:
    emotional_filter = EmotionalFilterResult(
        is_emotionally_relevant=True,
        confidence=0.8,
        categories=["anxiety"],
        risk_hint="none",
    )

    result = analyze_with_heuristics("אני ממש לחוץ מהמבחן מחר", emotional_filter)

    assert result.features.should_store is True
    assert result.features.emotion_scores.anxiety == 0.75
    assert result.features.theme_scores.academic_pressure == 0.8
    assert result.summary_for_embedding


class FakeMessage:
    content = """
    {
      "features": {
        "should_store": true,
        "signal_strength": 0.82,
        "risk_level": "none",
        "emotion_scores": {
          "anxiety": 0.8,
          "sadness": 0.2,
          "anger": 0,
          "loneliness": 0.1,
          "shame": 0.3,
          "hopelessness": 0
        },
        "cbt_pattern_scores": {
          "catastrophizing": 0.6,
          "all_or_nothing": 0,
          "mind_reading": 0.3,
          "overgeneralization": 0,
          "self_blame": 0,
          "avoidance": 0.4
        },
        "theme_scores": {
          "school": 0.9,
          "friends": 0.2,
          "parents": 0,
          "ai_dependency": 0,
          "academic_pressure": 0.8,
          "social_rejection": 0.1,
          "bullying": 0
        },
        "protective_signal_scores": {
          "seeking_help": 0.4,
          "future_orientation": 0,
          "trusted_adult": 0,
          "problem_solving": 0.3,
          "social_support": 0
        },
        "confidence": 0.87,
        "provider": "openai"
      },
      "summary_for_embedding": "The child expresses anxiety about academic pressure."
    }
    """


class FakeChoice:
    message = FakeMessage()


class FakeCompletion:
    choices = [FakeChoice()]


class FakeCompletions:
    def create(self, **kwargs):
        return FakeCompletion()


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_openai_analyzer_parses_structured_features() -> None:
    emotional_filter = EmotionalFilterResult(
        is_emotionally_relevant=True,
        confidence=0.85,
        categories=["anxiety"],
        risk_hint="none",
    )
    service = OpenAIPsychologicalAnalyzer(
        api_key="test-key",
        model="test-model",
        client=FakeClient(),
    )

    result = service.analyze("אני ממש לחוץ מהמבחן מחר", emotional_filter)

    assert result.features.should_store is True
    assert result.features.emotion_scores.anxiety == 0.8
    assert result.features.theme_scores.school == 0.9
    assert result.features.provider == "openai"
    assert result.summary_for_embedding == "The child expresses anxiety about academic pressure."

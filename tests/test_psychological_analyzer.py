from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.openai_analyzer import OpenAIPsychologicalAnalyzer


def test_heuristic_analyzer_returns_compact_scores_without_embedding_summary() -> None:
    result = analyze_with_heuristics("I feel overwhelmed before tomorrow's exam.")

    assert result.features.should_store is True
    assert result.features.scores.anxiety_stress == 7
    assert result.features.scores.negative_emotion == 7
    assert result.summary_for_embedding is None


class FakeMessage:
    content = """
    {
      "features": {
        "should_store": true,
        "signal_strength": 0.82,
        "risk_level": "none",
        "scores": {
          "positive_emotion": 5,
          "negative_emotion": 4,
          "loneliness": 1,
          "anxiety_stress": 8,
          "hopelessness": 1,
          "self_worth_low": 3,
          "risk": 1
        },
        "confidence": 0.87,
        "provider": "openai"
      }
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


def test_openai_analyzer_parses_compact_structured_scores() -> None:
    service = OpenAIPsychologicalAnalyzer(
        api_key="test-key",
        model="test-model",
        client=FakeClient(),
    )

    result = service.analyze("I feel anxious about school.")

    assert result.features.should_store is True
    assert result.features.scores.anxiety_stress == 8
    assert result.features.scores.negative_emotion == 4
    assert result.features.provider == "openai"
    assert result.summary_for_embedding is None

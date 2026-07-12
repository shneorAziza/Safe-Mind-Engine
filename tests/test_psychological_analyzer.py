import json

from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.bedrock_analyzer import BedrockPsychologicalAnalyzer
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


class FakeBedrockBody:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload.encode("utf-8")


class FakeBedrockClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.kwargs = None

    def invoke_model(self, **kwargs):
        self.kwargs = kwargs
        return {
            "body": FakeBedrockBody(
                json.dumps({"content": [{"type": "text", "text": self.text}]})
            )
        }


def test_bedrock_analyzer_parses_claude_messages_response() -> None:
    model_json = """
    {
      "features": {
        "should_store": true,
        "signal_strength": 0.74,
        "risk_level": "low",
        "scores": {
          "positive_emotion": 4,
          "negative_emotion": 5,
          "loneliness": 2,
          "anxiety_stress": 7,
          "hopelessness": 1,
          "self_worth_low": 2,
          "risk": 1
        },
        "confidence": 0.84,
        "provider": "bedrock"
      }
    }
    """
    fake_client = FakeBedrockClient(model_json)
    service = BedrockPsychologicalAnalyzer(
        model="anthropic.test-model",
        region="us-east-1",
        client=fake_client,
    )

    result = service.analyze("I feel anxious about school.")

    assert result.features.provider == "bedrock"
    assert result.features.scores.anxiety_stress == 7
    assert fake_client.kwargs["modelId"] == "anthropic.test-model"

import json

from safe_mind.signals.openai_emotional_filter import OpenAIEmotionalFilter
from safe_mind.signals.bedrock_emotional_filter import BedrockEmotionalFilter


class FakeMessage:
    content = (
        '{"is_emotionally_relevant":true,"confidence":0.91,'
        '"categories":["anxiety"],"risk_hint":"none"}'
    )


class FakeChoice:
    message = FakeMessage()


class FakeCompletion:
    choices = [FakeChoice()]


class FakeCompletions:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeCompletion()


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_openai_filter_parses_model_json_response() -> None:
    service = OpenAIEmotionalFilter(api_key="test-key", model="test-model", client=FakeClient())

    result = service.filter("I am worried about everything.")

    assert result.is_emotionally_relevant is True
    assert result.confidence == 0.91
    assert result.categories == ["anxiety"]
    assert result.risk_hint == "none"
    assert result.provider == "openai"


class FakeHebrewSafetyMessage:
    content = (
        '{"is_emotionally_relevant":true,"confidence":0.7,'
        '"categories":["hopelessness"],"risk_hint":"possible"}'
    )


class FakeHebrewSafetyChoice:
    message = FakeHebrewSafetyMessage()


class FakeHebrewSafetyCompletion:
    choices = [FakeHebrewSafetyChoice()]


class FakeHebrewSafetyCompletions:
    def create(self, **kwargs):
        return FakeHebrewSafetyCompletion()


class FakeHebrewSafetyChat:
    def __init__(self):
        self.completions = FakeHebrewSafetyCompletions()


class FakeHebrewSafetyClient:
    def __init__(self):
        self.chat = FakeHebrewSafetyChat()


def test_openai_filter_overrides_missed_hebrew_life_ending_language() -> None:
    service = OpenAIEmotionalFilter(
        api_key="test-key",
        model="test-model",
        client=FakeHebrewSafetyClient(),
    )

    result = service.filter("\u05dc\u05e4\u05e2\u05de\u05d9\u05dd \u05d0\u05e0\u05d9 \u05d7\u05d5\u05e9\u05d1 \u05e9\u05dc\u05d0 \u05d1\u05d0 \u05dc\u05d9 \u05dc\u05d7\u05d9\u05d5\u05ea \u05d9\u05d5\u05ea\u05e8")

    assert result.is_emotionally_relevant is True
    assert result.risk_hint == "urgent"
    assert "safety_risk" in result.categories
    assert result.provider == "openai"


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


def test_bedrock_filter_parses_claude_messages_response() -> None:
    fake_client = FakeBedrockClient(
        '{"is_emotionally_relevant":true,"confidence":0.88,'
        '"categories":["loneliness"],"risk_hint":"none"}'
    )
    service = BedrockEmotionalFilter(
        model="anthropic.test-model",
        region="us-east-1",
        client=fake_client,
    )

    result = service.filter("Nobody understands me.")

    assert result.provider == "bedrock"
    assert result.categories == ["loneliness"]
    assert result.confidence == 0.88
    assert fake_client.kwargs["modelId"] == "anthropic.test-model"

from safe_mind.bedrock_runtime import BedrockClaudeMessagesClient, BedrockRuntimeClient
from safe_mind.signals.emotional_filter import EmotionalFilterResult, filter_emotional_relevance
from safe_mind.signals.openai_emotional_filter import (
    SYSTEM_PROMPT,
    _apply_safety_overrides,
)


class BedrockEmotionalFilter:
    def __init__(
        self,
        *,
        model: str,
        region: str,
        client: BedrockRuntimeClient | None = None,
    ) -> None:
        self.model = model
        self.region = region
        self.client = BedrockClaudeMessagesClient(model=model, region=region, client=client)

    def filter(self, text: str, *, allow_fallback: bool = True) -> EmotionalFilterResult:
        try:
            content = self.client.complete_json(system_prompt=SYSTEM_PROMPT, user_content=text)
            result = EmotionalFilterResult.model_validate_json(content)
            result = result.model_copy(update={"provider": "bedrock"})
            return _apply_safety_overrides(text, result)
        except Exception:
            if not allow_fallback:
                raise
            return filter_emotional_relevance(text)

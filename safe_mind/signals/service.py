from safe_mind.core.config import settings
from safe_mind.signals.bedrock_emotional_filter import BedrockEmotionalFilter
from safe_mind.signals.emotional_filter import EmotionalFilterResult, filter_emotional_relevance
from safe_mind.signals.openai_emotional_filter import OpenAIEmotionalFilter


def run_emotional_filter(text: str, *, allow_fallback: bool = True) -> EmotionalFilterResult:
    if settings.emotional_filter_provider == "openai" and settings.openai_api_key:
        return OpenAIEmotionalFilter(
            api_key=settings.openai_api_key,
            model=settings.openai_emotional_filter_model,
        ).filter(text, allow_fallback=allow_fallback)

    if settings.emotional_filter_provider == "bedrock":
        return BedrockEmotionalFilter(
            model=settings.bedrock_emotional_filter_model,
            region=settings.bedrock_region,
        ).filter(text, allow_fallback=allow_fallback)

    return filter_emotional_relevance(text)

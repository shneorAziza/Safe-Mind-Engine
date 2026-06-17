from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.models import PsychologicalAnalysisResult
from safe_mind.analysis.openai_analyzer import OpenAIPsychologicalAnalyzer
from safe_mind.core.config import settings
from safe_mind.signals.emotional_filter import EmotionalFilterResult


def run_psychological_analyzer(
    text: str,
    emotional_filter: EmotionalFilterResult,
    *,
    allow_fallback: bool = True,
) -> PsychologicalAnalysisResult | None:
    if not emotional_filter.is_emotionally_relevant:
        return None

    if settings.psychological_analyzer_provider == "openai" and settings.openai_api_key:
        return OpenAIPsychologicalAnalyzer(
            api_key=settings.openai_api_key,
            model=settings.openai_psychological_analyzer_model,
        ).analyze(text, emotional_filter, allow_fallback=allow_fallback)

    return analyze_with_heuristics(text, emotional_filter)

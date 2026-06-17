from safe_mind.core.config import settings
from safe_mind.privacy.redactor import redact_text
from safe_mind.analysis.service import run_psychological_analyzer
from safe_mind.signals.service import run_emotional_filter


def main() -> None:
    sample_text = "I feel anxious and overwhelmed today. Call me at 052-123-4567."
    redaction = redact_text(sample_text)
    emotional_filter = run_emotional_filter(redaction.redacted_text)
    psychological_analysis = run_psychological_analyzer(
        redaction.redacted_text,
        emotional_filter,
    )

    print(
        {
            "configured_provider": settings.emotional_filter_provider,
            "has_api_key": bool(settings.openai_api_key),
            "model": settings.openai_emotional_filter_model,
            "redacted_text": redaction.redacted_text,
            "privacy": {
                "pii_detected": redaction.pii_detected,
                "pii_types": redaction.pii_types,
                "redaction_count": redaction.redaction_count,
                "risk_level": redaction.risk_level,
            },
            "emotional_filter": emotional_filter.model_dump(),
            "signal_features": (
                psychological_analysis.features.model_dump() if psychological_analysis else None
            ),
            "has_temporary_embedding_summary": bool(
                psychological_analysis.summary_for_embedding if psychological_analysis else False
            ),
        }
    )


if __name__ == "__main__":
    main()

from safe_mind.core.config import settings
from safe_mind.privacy.redactor import redact_text
from safe_mind.analysis.service import run_psychological_analyzer


def main() -> None:
    sample_text = "I feel anxious and overwhelmed today. Call me at 052-123-4567."
    redaction = redact_text(sample_text)
    psychological_analysis = run_psychological_analyzer(redaction.redacted_text)

    print(
        {
            "configured_provider": settings.psychological_analyzer_provider,
            "has_api_key": bool(settings.openai_api_key),
            "model": settings.openai_psychological_analyzer_model,
            "redacted_text": redaction.redacted_text,
            "privacy": {
                "pii_detected": redaction.pii_detected,
                "pii_types": redaction.pii_types,
                "redaction_count": redaction.redaction_count,
                "risk_level": redaction.risk_level,
            },
            "signal_features": (
                psychological_analysis.features.model_dump() if psychological_analysis else None
            ),
            "embeddings_enabled": settings.enable_embeddings,
        }
    )


if __name__ == "__main__":
    main()

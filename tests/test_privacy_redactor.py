from safe_mind.privacy.redactor import redact_text


def test_redacts_clear_personal_identifiers() -> None:
    result = redact_text(
        "Email me at kid@example.com, call 052-123-4567, or visit https://example.com/me."
    )

    assert result.redacted_text == "Email me at [EMAIL], call [PHONE], or visit [URL]."
    assert result.pii_detected is True
    assert result.pii_types == ["EMAIL", "URL", "PHONE"]
    assert result.redaction_count == 3
    assert result.risk_level == "high"


def test_keeps_non_pii_text_unchanged() -> None:
    text = "I feel overwhelmed today and I do not know what to do."

    result = redact_text(text)

    assert result.redacted_text == text
    assert result.pii_detected is False
    assert result.pii_types == []
    assert result.redaction_count == 0
    assert result.risk_level == "low"

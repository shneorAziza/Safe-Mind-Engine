import re
from collections.abc import Iterable
from dataclasses import dataclass

from safe_mind.privacy.models import PiiType, RedactionResult


@dataclass(frozen=True)
class RedactionRule:
    pii_type: PiiType
    replacement: str
    pattern: re.Pattern[str]


REDACTION_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        pii_type="EMAIL",
        replacement="[EMAIL]",
        pattern=re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    RedactionRule(
        pii_type="URL",
        replacement="[URL]",
        pattern=re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE),
    ),
    RedactionRule(
        pii_type="PHONE",
        replacement="[PHONE]",
        pattern=re.compile(
            r"(?<!\d)(?:\+?972[-\s]?)?0?(?:5\d|[23489])[-\s]?\d{3}[-\s]?\d{4}(?!\d)"
        ),
    ),
    RedactionRule(
        pii_type="ID_NUMBER",
        replacement="[ID_NUMBER]",
        pattern=re.compile(r"(?<!\d)\d{8,10}(?!\d)"),
    ),
    RedactionRule(
        pii_type="ADDRESS",
        replacement="[ADDRESS]",
        pattern=re.compile(
            r"\b(?:רחוב|רח'|street|st\.?|avenue|ave\.?|road|rd\.?)\s+[\w\u0590-\u05FF\s'.-]+"
            r"\s+\d{1,4}\b",
            re.IGNORECASE,
        ),
    ),
)


def redact_text(text: str, rules: Iterable[RedactionRule] = REDACTION_RULES) -> RedactionResult:
    redacted_text = text
    pii_types: list[PiiType] = []
    redaction_count = 0

    for rule in rules:
        redacted_text, count = rule.pattern.subn(rule.replacement, redacted_text)
        if count:
            pii_types.append(rule.pii_type)
            redaction_count += count

    unique_pii_types = list(dict.fromkeys(pii_types))
    return RedactionResult(
        redacted_text=redacted_text,
        pii_detected=redaction_count > 0,
        pii_types=unique_pii_types,
        redaction_count=redaction_count,
        risk_level=_risk_level(unique_pii_types, redaction_count),
    )


def _risk_level(pii_types: list[PiiType], redaction_count: int) -> str:
    if redaction_count >= 3 or "ID_NUMBER" in pii_types:
        return "high"
    if redaction_count >= 1:
        return "medium"
    return "low"

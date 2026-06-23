# Current Pipeline

## Purpose

The backend now supports the full internal alert-evaluation loop without a first-stage message filter.

```text
message
  -> privacy redaction
  -> psychological signal analysis
  -> compact JSON signal scores
  -> signal-feature storage
  -> daily trend + alert decision
```

The parent-facing app and push delivery service are still out of scope.
What exists today is the backend decision engine that can decide whether a parent push should be sent.

## Endpoint

```http
POST /v1/ingest/messages
```

Example request:

```json
{
  "event_id": "6fbdad90-89c7-4f7a-85a3-679a0ce29952",
  "child_user_id": "fd588728-5478-44c7-b887-673581a571bc",
  "device_id": "1736d0fe-f1a4-410e-bca2-696d36c029c3",
  "occurred_at": "2026-06-15T10:15:00Z",
  "source_type": "notification",
  "source_app": "example.ai.app",
  "text": "I feel overwhelmed and cannot sleep before tomorrow's exam.",
  "locale": "en"
}
```

## Stage 1: Privacy Redaction

Files:

- [safe_mind/privacy/redactor.py](../safe_mind/privacy/redactor.py)
- [safe_mind/privacy/models.py](../safe_mind/privacy/models.py)

This stage removes PII patterns before model calls.

Outputs include:

- `pii_detected`
- `pii_types`
- `redaction_count`
- `risk_level`

`redacted_text` is used internally by later stages but is not stored in the database.

## Stage 2: Psychological Signal Analyzer

Files:

- [safe_mind/analysis/service.py](../safe_mind/analysis/service.py)
- [safe_mind/analysis/openai_analyzer.py](../safe_mind/analysis/openai_analyzer.py)
- [safe_mind/analysis/heuristic_analyzer.py](../safe_mind/analysis/heuristic_analyzer.py)

This stage converts every privacy-redacted message into numeric and enumerated features.

Important outputs:

- `signal_strength`
- `risk_level`
- `scores.positive_emotion`
- `scores.negative_emotion`
- `scores.loneliness`
- `scores.anxiety_stress`
- `scores.hopelessness`
- `scores.self_worth_low`
- `scores.risk`

No summary, evidence phrase, quote, raw text, or redacted text is stored.
`signal_strength` is stored as metadata, while the alert engine uses the compact scores.

## Stage 3: Signal Storage

Files:

- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)

If `features.should_store=true`, the current pilot pipeline stores:

- numeric and enumerated features
- timestamps
- pseudonymous ids

The following are not stored:

- raw text
- redacted text
- summary text
- quotes

## Stage 4: Trend and Alert Decision

Files:

- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/alerts/models.py](../safe_mind/alerts/models.py)

After storage, the engine evaluates the child's alert state:

- fixed baseline from the first 10 calendar days
- daily score from that day's compact psychological scores
- baseline score from the average baseline-day scores
- deviation threshold of `+0.2` over baseline score
- alert gate of `3 consecutive deviation days`
- cooldown after a `send` decision

The output is an internal `ParentAlertDecision`.

## What the Endpoint Returns

The ingestion response includes:

- privacy summary
- signal features
- storage summary
- `alert_decision` when a stored signal triggered trend evaluation

The endpoint does not send a real push notification. It only records whether the engine would send one.

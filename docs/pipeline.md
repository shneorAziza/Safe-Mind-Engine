# Current Pipeline

## Purpose

The backend now supports the full internal alert-evaluation loop, not only a first-stage emotional filter.

```text
message
  -> privacy redaction
  -> emotional relevance filter
  -> psychological signal analysis
  -> temporary embedding summary
  -> embedding vector
  -> vector/features storage
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

## Stage 2: Emotional Relevance Filter

Files:

- [safe_mind/signals/service.py](../safe_mind/signals/service.py)
- [safe_mind/signals/openai_emotional_filter.py](../safe_mind/signals/openai_emotional_filter.py)
- [safe_mind/signals/emotional_filter.py](../safe_mind/signals/emotional_filter.py)

By default this stage uses the configured provider from `.env`.
When OpenAI is enabled, the result is still protected by local urgent-safety overrides.

Example output:

```json
{
  "is_emotionally_relevant": true,
  "confidence": 0.85,
  "categories": ["anxiety"],
  "risk_hint": "none",
  "provider": "openai"
}
```

If `is_emotionally_relevant=false`, the pipeline stops here.

## Stage 3: Psychological Signal Analyzer

Files:

- [safe_mind/analysis/service.py](../safe_mind/analysis/service.py)
- [safe_mind/analysis/openai_analyzer.py](../safe_mind/analysis/openai_analyzer.py)
- [safe_mind/analysis/heuristic_analyzer.py](../safe_mind/analysis/heuristic_analyzer.py)

This stage converts an emotionally relevant message into numeric and enumerated features.

Important outputs:

- `signal_strength`
- `risk_level`
- `emotion_scores`
- `theme_scores`
- `protective_signal_scores`
- `summary_for_embedding`

`summary_for_embedding` is temporary and must not be stored as text.
`signal_strength` is still stored as metadata, but it is no longer the primary input to the alert engine.

## Stage 4: Embedding and Storage

Files:

- [safe_mind/embeddings/openai_embeddings.py](../safe_mind/embeddings/openai_embeddings.py)
- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)

If `features.should_store=true`, the pipeline creates an embedding and stores:

- vector
- embedding metadata
- numeric and enumerated features
- timestamps
- pseudonymous ids

The following are not stored:

- raw text
- redacted text
- summary text
- quotes

## Stage 5: Trend and Alert Decision

Files:

- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/alerts/models.py](../safe_mind/alerts/models.py)

After storage, the engine evaluates the child's alert state:

- fixed baseline centroid from the first 10 calendar days
- daily score from cosine distance between the day's vector centroid and the fixed baseline centroid
- baseline score from the average baseline-day distances
- deviation threshold of `+0.2` over baseline score
- alert gate of `3 deviations in 5 days`
- cooldown after a `send` decision

The output is an internal `ParentAlertDecision`.

## What the Endpoint Returns

The ingestion response includes:

- privacy summary
- emotional filter result
- signal features when analysis ran
- storage summary
- `alert_decision` when a stored signal triggered trend evaluation

The endpoint does not send a real push notification. It only records whether the engine would send one.

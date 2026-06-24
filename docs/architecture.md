# SafeMind Backend Architecture

## System Boundaries

The current system is a backend plus internal evaluation tooling.

Out of scope today:

- Android collection implementation
- child-facing product UI
- parent-facing product UI
- real push delivery implementation

In scope today:

- ingesting child-device message events
- privacy redaction before model calls
- psychological signal extraction
- compact signal-feature storage
- closed-day daily alert-decision logic
- outbound callback to the Firebase/Next backend for push decisions
- MongoDB Atlas production storage
- health/readiness checks and basic metrics
- internal evaluation and dashboard tooling

## Current Built Flow

```text
POST /v1/integrations/next/messages
  -> privacy redaction
  -> psychological analyzer
  -> MongoDB daily signal aggregation
  -> acknowledgement only

scripts/finalize_previous_day.py --send-alerts
  -> evaluate previous closed day
  -> update finalized alert decision
  -> callback to Firebase/Next backend when push should be sent
```

## Target Product Flow

```text
Child device
  -> Firebase/Next backend ingestion
  -> SafeMind analyzer backend
  -> Privacy-first AI pipeline
  -> Stored numeric features only
  -> Fixed baseline + closed-day deviation detection
  -> Firebase/Next parent notification service
```

## Key Modules

```text
safe_mind/
  api/
    health.py
    ingestion.py
    metrics.py
    next_integration.py
    eval_ui.py
  core/
    config.py
  privacy/
    models.py
    redactor.py
  signals/
    emotional_filter.py
    openai_emotional_filter.py
    service.py
  analysis/
    heuristic_analyzer.py
    openai_analyzer.py
    service.py
  embeddings/
    openai_embeddings.py
    service.py
  alerts/
    models.py
    engine.py
    finalization.py
    finalization_job.py
  integrations/
    next_alerts.py
  storage/
    mongo_store.py
    vector_store.py
  pipeline.py
```

## Storage Model

MongoDB Atlas is used for the real pilot signal store. SQLite remains available
as a local fallback for tests and offline development. Production rejects SQLite.

Stored data includes:

- numeric/enumerated signal features
- timestamps
- pseudonymous ids
- alert decisions

Stored data must not include:

- raw text
- redacted text
- summary text
- quotes

## Alert Engine Design

The internal alert engine now works over compact stored psychological scores.

Current policy:

- first 10 calendar days form a fixed personal baseline
- each day gets a metric vector from that day's compact psychological scores
- baseline vector is the average vector during the baseline window
- a deviation is based on per-metric thresholds from baseline
- a push decision requires `3 consecutive finalized deviation days`
- ingestion can update same-day averages, but push decisions are only sent after closed-day finalization

## Evaluation Surfaces

The active internal evaluation surface is the visual Eval UI:

- [eval-ui.md](eval-ui.md)

The Eval UI now covers both:

- per-message pipeline stages
- per-user 30-day alert dashboards

## Operations

Runtime health:

```text
GET /health/live
GET /health/ready
```

Basic pilot metrics:

```text
GET /metrics
```

# SafeMind Backend Architecture

## System Boundaries

The current system is a backend plus internal evaluation tooling.

Out of scope today:

- Android collection implementation
- child-facing product UI
- parent-facing product UI
- production push delivery service
- production database and auth stack

In scope today:

- ingesting child-device message events
- privacy redaction before model calls
- emotional relevance filtering
- psychological signal extraction
- embeddings and vector storage
- daily alert-decision logic
- internal evaluation and dashboard tooling

## Current Built Flow

```text
POST /v1/ingest/messages
  -> privacy redaction
  -> emotional relevance filter
  -> psychological analyzer
  -> embeddings
  -> SQLite vector/features storage
  -> daily alert decision
```

## Target Product Flow

```text
Child device
  -> Backend ingestion
  -> Privacy-first AI pipeline
  -> Stored numeric/vector features only
  -> Fixed baseline + deviation detection
  -> Parent notification service
```

## Key Modules

```text
safe_mind/
  api/
    health.py
    ingestion.py
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
  storage/
    vector_store.py
  pipeline.py
```

## Storage Model

SQLite is used today for pilot simplicity.

Stored data includes:

- embedding vectors
- embedding model metadata
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

The internal alert engine now works primarily over stored embedding vectors.

Current policy:

- first 10 calendar days form a fixed vector baseline
- each day gets a daily vector centroid from that day's stored embeddings
- daily score is the cosine distance between the daily centroid and the fixed baseline centroid
- baseline score is the average baseline-day distance from the baseline centroid
- a deviation requires `daily_score - baseline_score >= 0.2`
- a push decision requires `3 deviations in 5 days`
- cooldown suppresses immediate repeat pushes

## Evaluation Surfaces

There are two internal evaluation paths:

- dataset-based filter evaluation
  - [evaluation.md](evaluation.md)
- visual pipeline and alert inspection
  - [eval-ui.md](eval-ui.md)

The Eval UI now covers both:

- per-message pipeline stages
- per-user 30-day alert dashboards

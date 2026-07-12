# SafeMind Backend Architecture

## System Boundaries

The current system is a backend plus internal evaluation tooling.

Out of scope today:

- Android collection implementation
- child-facing product UI
- parent-facing product UI
- parent-facing UI

In scope today:

- WhatsApp-code registration/login
- permanent app-token authentication
- local parent phone storage
- ingesting child-device message events
- privacy redaction before model calls
- psychological signal extraction
- compact signal-feature storage
- closed-day daily alert-decision logic
- outbound WhatsApp template delivery for finalized parent alerts
- MongoDB Atlas production storage
- health/readiness checks and basic metrics
- internal evaluation and dashboard tooling

## Current Built Flow

```text
POST /v1/auth/start
  -> send WhatsApp verification code

POST /v1/auth/verify
  -> create/update local app user
  -> return permanent token

POST /v1/app/messages
  -> verify bearer token and matching deviceId
  -> privacy redaction
  -> psychological analyzer
  -> MongoDB daily signal aggregation
  -> acknowledgement only

scripts/finalize_previous_day.py --send-alerts
  -> evaluate previous closed day
  -> update finalized alert decision
  -> resolve parent phone from local app user DB
  -> send WhatsApp template alert to parent
```

## Target Product Flow

```text
Child device
  -> frontend/backend collector
  -> SafeMind app-authenticated ingestion
  -> Privacy-first AI pipeline
  -> Stored numeric features only
  -> Fixed baseline + closed-day deviation detection
  -> WhatsApp parent alert
```

## Key Modules

```text
safe_mind/
  api/
    app_auth.py
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
    bedrock_emotional_filter.py
    openai_emotional_filter.py
    service.py
  analysis/
    bedrock_analyzer.py
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
    parent_contacts.py
    sms_verification.py
    whatsapp.py
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
- an alert decision requires `3 different metrics that each reached a 3-day consecutive deviation streak on the same finalized day`
- ingestion can update same-day averages, but parent WhatsApp alerts are only sent after closed-day finalization

## Evaluation Surfaces

The active internal evaluation surface is the visual Eval UI:

- [eval-ui.md](eval-ui.md)

The Eval UI now covers:

- large historical dataset simulation through the live pipeline
- per-user alert dashboards with baseline, deviation, and parent-alert decisions
- optional real WhatsApp delivery for finalized alert days

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

## Model Providers

The active production provider remains OpenAI with `gpt-4o-mini` for both model
scoring stages.

Amazon Bedrock provider support exists in code for a future switch, but it is
not the active deployment path. Do not replace `gpt-4o-mini` with a Bedrock
model unless the user explicitly asks to change models.

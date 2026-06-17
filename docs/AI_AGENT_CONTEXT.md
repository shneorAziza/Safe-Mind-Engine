# SafeMind AI Agent Context

This file is the main starting point for any new AI agent working on this repository.

Read this before editing code.

## Project Summary

SafeMind is a Python/FastAPI backend for a pilot that receives messages from a child's Android-side app, processes them through a privacy-first AI pipeline, and eventually produces internal trend signals that can trigger a parent notification.

The current product is not the final parent/child app. It is the backend plus internal evaluation tools.

## Current Scope

Implemented:

- FastAPI backend.
- Message ingestion endpoint.
- Privacy redaction.
- Emotional relevance filtering.
- Psychological signal analysis.
- OpenAI embeddings.
- Local SQLite vector store.
- Daily trend / baseline engine over stored embedding vectors.
- Internal parent-alert decision engine with a 3-of-5 day gate.
- Internal Eval UI for manual pipeline inspection.
- Internal alert timeline dashboard for inspecting baseline/gate behavior by child user id.
- JSONL dataset for first-stage filter evaluation.

Not implemented yet:

- Android collector.
- Parent app.
- Push notifications.
- Production DB.
- Real user auth.
- Production-grade retention jobs.

## Core Privacy Rule

The pilot spec requires that text is not stored after processing.

Do not store:

- raw message text,
- redacted text,
- `summary_for_embedding`,
- evidence phrases,
- direct quotes from the child conversation.

Allowed future storage:

- embedding vector,
- numeric signal features,
- enums,
- timestamps,
- pseudonymous ids,
- model/pipeline versions,
- parent feedback values.

The Eval UI and debug scripts may display raw/redacted/summary text locally for manual testing, but this must remain internal and must not be persisted.

## Current Pipeline

```text
Incoming message
  -> privacy redaction
  -> emotional relevance filter
  -> psychological signal analyzer
  -> temporary summary_for_embedding
  -> OpenAI embedding
  -> local vector store with vector + metadata only
  -> internal daily trend / parent-alert decision
```

Implementation entry point:

- [safe_mind/pipeline.py](../safe_mind/pipeline.py)

## Main Runtime Endpoints

### Health

```http
GET /health
```

### Ingest Message

```http
POST /v1/ingest/messages
```

Defined in:

- [safe_mind/api/ingestion.py](../safe_mind/api/ingestion.py)
- [safe_mind/schemas/ingestion.py](../safe_mind/schemas/ingestion.py)

This endpoint processes one message through the pipeline. Depending on configuration, it may persist vectors.

### Internal Eval UI

```http
GET /eval
POST /eval/run
GET /eval/alerts/timeline
GET /eval/alerts/users
```

Defined in:

- [safe_mind/api/eval_ui.py](../safe_mind/api/eval_ui.py)

This is an internal testing tool, not a product UI.

## Configuration

Expected `.env` values:

```env
SAFE_MIND_ENV=local
SAFE_MIND_API_TITLE=SafeMind Backend

SAFE_MIND_EMOTIONAL_FILTER_PROVIDER=openai
SAFE_MIND_OPENAI_EMOTIONAL_FILTER_MODEL=gpt-4o-mini

SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER=openai
SAFE_MIND_OPENAI_PSYCHOLOGICAL_ANALYZER_MODEL=gpt-4o-mini

SAFE_MIND_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SAFE_MIND_VECTOR_DB_PATH=data/safe_mind_vectors.sqlite3
SAFE_MIND_PERSIST_SIGNALS=true
SAFE_MIND_PIPELINE_VERSION=v1

OPENAI_API_KEY=...
```

Configuration is defined in:

- [safe_mind/core/config.py](../safe_mind/core/config.py)

## Package Map

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
    models.py
    heuristic_analyzer.py
    openai_analyzer.py
    service.py
  embeddings/
    models.py
    openai_embeddings.py
    service.py
  alerts/
    models.py
    engine.py
  storage/
    models.py
    vector_store.py
  pipeline.py
```

## Stage Details

### 1. Privacy Redaction

Files:

- [safe_mind/privacy/redactor.py](../safe_mind/privacy/redactor.py)
- [safe_mind/privacy/models.py](../safe_mind/privacy/models.py)

Currently redacts:

- email,
- phone,
- URL,
- ID-like numbers,
- basic addresses.

This stage returns a redacted text for internal processing and a privacy summary.

### 2. Emotional Relevance Filter

Files:

- [safe_mind/signals/service.py](../safe_mind/signals/service.py)
- [safe_mind/signals/openai_emotional_filter.py](../safe_mind/signals/openai_emotional_filter.py)
- [safe_mind/signals/emotional_filter.py](../safe_mind/signals/emotional_filter.py)

Purpose:

```text
Decide whether the message should pass to the next stage.
```

It is not intended to produce final psychological analysis.

OpenAI is used when configured. There is a heuristic fallback.

There is also a local urgent-safety regex override for phrases such as not wanting to live or self-harm language.

### 3. Psychological Signal Analyzer

Files:

- [safe_mind/analysis/models.py](../safe_mind/analysis/models.py)
- [safe_mind/analysis/openai_analyzer.py](../safe_mind/analysis/openai_analyzer.py)
- [safe_mind/analysis/heuristic_analyzer.py](../safe_mind/analysis/heuristic_analyzer.py)
- [safe_mind/analysis/service.py](../safe_mind/analysis/service.py)

Purpose:

```text
Convert a filtered message into numeric/enumerated internal signals.
```

It does not diagnose and does not produce a clinical opinion.

It returns:

- `features`: allowed future storage,
- `summary_for_embedding`: temporary text for vectorization only.

### 4. Embeddings

Files:

- [safe_mind/embeddings/openai_embeddings.py](../safe_mind/embeddings/openai_embeddings.py)
- [safe_mind/embeddings/service.py](../safe_mind/embeddings/service.py)

Current model:

```text
text-embedding-3-small
```

The vector is generated from `summary_for_embedding`, then the summary must be discarded.

### 5. Local Vector Store

Files:

- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)
- [safe_mind/storage/models.py](../safe_mind/storage/models.py)

Current store:

```text
data/safe_mind_vectors.sqlite3
```

This is a pilot-friendly local storage choice. It can later be replaced by Postgres + pgvector or a managed vector DB.

Current table columns:

```text
id
event_id
child_user_id
device_id
occurred_at
source_app
vector_json
embedding_model
embedding_dimensions
features_json
pipeline_version
created_at
```

No text columns should be added without explicitly revisiting the privacy decision.

The same SQLite database also stores internal parent-alert decisions in
`parent_alert_decisions`. This table stores only numeric/enumerated alert
metadata:

```text
id
child_user_id
target_day
should_send_push
reason
daily_score
baseline_score
deviations_in_window
gate_window_days
required_deviation_days
message_count
created_at
```

### 6. Trend / Alert Decision Engine

Files:

- [safe_mind/alerts/models.py](../safe_mind/alerts/models.py)
- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)

Purpose:

```text
Convert stored embedding vectors into a daily semantic-drift score, compare it to the
child's fixed first-10-day baseline, and decide whether a parent push should be sent.
```

Current pilot policy:

- Daily score: cosine distance between that day's vector centroid and the
  child's fixed baseline centroid.
- Baseline: the average of baseline-day cosine distances inside the first
  10 calendar days after the child's first stored signal.
- Fixed baseline centroid: the mean vector built from the first 10 calendar
  days after the child's first stored signal.
- No alert decisions are eligible during the first 10-day calibration period.
- Minimum baseline: 3 signal days inside the first 10 calendar days before a
  deviation can count.
- Deviation: `daily_score - baseline_score >= 0.2`.
- Alert gate: 3 deviation days inside the last 5 calendar days.
- Cooldown: 5 days after an alert decision that recommends sending a push.

The decision engine does not send push notifications itself. It returns and
persists an internal `ParentAlertDecision` with `should_send_push`.

## Internal Eval UI

Run the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn safe_mind.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/eval
```

The Eval UI is displayed as a stage-by-stage funnel:

```text
Raw Messages
  -> Privacy
  -> Emotional Filter
  -> Psychological Analyzer
  -> Embedding: Vector + Metadata
```

Each message is processed independently.
Messages that are filtered out do not appear in later stages.

Default behavior:

- creates embedding preview,
- shows vector and metadata preview,
- does not persist to SQLite.

The Eval UI also includes an internal Alert Timeline dashboard:

- enter or reuse a `child_user_id`,
- inspect a 30-day default timeline,
- view fixed first-10-day baseline behavior,
- see daily vector distance, baseline distance, delta, deviation status, 3-of-5 count, push decision, and reason,
- optionally run one message per line as one calendar day for quick pilot simulations.

### Synthetic Alert Test User

A deterministic 30-day synthetic alert-engine user can be seeded into the local SQLite DB:

```powershell
.\.venv\Scripts\python.exe scripts\seed_alert_demo_data.py
```

Synthetic child user id:

```text
11111111-2222-4333-8444-555555555555
```

Expected behavior:

- `2026-06-01` through `2026-06-10`: fixed baseline period.
- `2026-06-17`: first `3 of 5` gate match, `should_send_push=true`.
- `2026-06-23`: second gate match after cooldown.

The seed writes numeric vectors and numeric/enumerated signal features only. It
does not store raw messages, redacted messages, summaries, evidence, or quotes.

### Synthetic Message Pipeline Test User

For an end-to-end local test of synthetic messages flowing through the pipeline
into the alert engine:

```powershell
.\.venv\Scripts\python.exe scripts\seed_message_pipeline_demo_data.py
```

Synthetic message-pipeline child user id:

```text
55555555-6666-4777-8888-999999999999
```

Expected behavior:

- `2026-07-01` through `2026-07-10`: baseline messages flow through the pipeline.
- `2026-07-19`: first `3 of 5` gate match, `should_send_push=true`.
- `2026-07-25`: second gate match after cooldown.

Known OpenAI-backed run:

- child user id: `55555555-6666-4777-8888-999999999999`
- signal rows: 30
- feature provider: `openai`
- embedding model: `text-embedding-3-small`
- push days under both the old seeded run and the rebuilt vector engine: `2026-07-19`, `2026-07-25`

By default this seed uses the configured runtime providers, including OpenAI
filter/analyzer/embedding when enabled in `.env`. This is the preferred
evaluation path because it tests model behavior as part of the pipeline.

For local offline development only, pass:

```powershell
.\.venv\Scripts\python.exe scripts\seed_message_pipeline_demo_data.py --local-offline
```

In `--local-offline` mode the script uses heuristic providers and a deterministic
local embedding. That mode should not be treated as a model-quality evaluation.

## Scripts

### Pipeline Debug

Run one or more messages from CLI:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_debug.py --no-persist --text "אני ממש לחוץ מהמבחן מחר"
```

Useful flags:

- `--no-persist`: creates embedding preview but does not write to DB.
- `--no-vector`: skips embedding entirely.
- `--file`: reads one message per line from a UTF-8 file.

### Filter Dataset Evaluation

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_filter_dataset.py
```

Dataset:

- [data/filter_eval_cases.jsonl](../data/filter_eval_cases.jsonl)

This evaluates the first filter stage only.

### Alert Decision Rebuild

```powershell
.\.venv\Scripts\python.exe scripts\rebuild_parent_alert_decisions.py
```

Use this after changing the alert engine logic so `parent_alert_decisions`
stored in SQLite are rebuilt from the existing vectors.

## Verification Commands

Always run before handing off changes:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Current expected test count at time of writing:

```text
25 passed
```

## Design/Architecture Decisions To Preserve

1. Backend only for now.
2. API keys stay server-side.
3. No raw/redacted/summary text should be stored.
4. The emotional filter only decides pass/fail for the next stage.
5. The analyzer extracts internal signals and must avoid diagnosis/clinical claims.
6. The embedding summary is temporary.
7. Vector storage currently uses SQLite for pilot simplicity.
8. Alert decisions are internal and must not expose raw scores or categories to the parent UI.
9. Eval UI is internal and removable.
10. Docs should be updated after meaningful completed stages or architecture decisions.

## Recommended Next Steps

Likely next work items:

- Improve the psychological analyzer prompt with the user's CBT/PERMA skill content.
- Add vector search/evaluation helpers.
- Add a simulation/debug script for multi-day alert engine scenarios.
- Tune the trend/alert thresholds against pilot simulations and parent feedback.
- Add retention/deletion mechanics for vector/features.
- Replace local SQLite with a production vector store when needed.

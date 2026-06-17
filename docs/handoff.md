# SafeMind Backend Handoff

## Current State

SafeMind is currently a backend-first pilot focused on the internal decision engine, not the final child app or parent app.

What exists today:

- FastAPI backend
- privacy redaction before model calls
- OpenAI-backed emotional relevance filter
- OpenAI-backed psychological analyzer
- OpenAI embeddings
- local SQLite vector store
- internal eval UI
- internal alert dashboard
- vector-based baseline and deviation engine

What is still out of scope:

- Android collector implementation
- parent-facing app
- production push delivery
- production auth
- production database stack

## Current Pipeline

```text
message
  -> privacy redaction
  -> emotional relevance filter
  -> psychological analyzer
  -> temporary summary_for_embedding
  -> embedding vector
  -> local vector/features storage
  -> vector-based baseline + deviation engine
  -> internal parent alert decision
```

Implementation entry points:

- [safe_mind/pipeline.py](../safe_mind/pipeline.py)
- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)

## Runtime Models

Configured in `.env`:

```env
SAFE_MIND_EMOTIONAL_FILTER_PROVIDER=openai
SAFE_MIND_OPENAI_EMOTIONAL_FILTER_MODEL=gpt-4o-mini

SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER=openai
SAFE_MIND_OPENAI_PSYCHOLOGICAL_ANALYZER_MODEL=gpt-4o-mini

SAFE_MIND_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=...
```

## Privacy Rule

Do not persist:

- raw text
- redacted text
- `summary_for_embedding`
- direct quotes
- evidence phrases

Allowed persistence:

- embedding vectors
- numeric/enumerated features
- timestamps
- pseudonymous ids
- pipeline/model metadata
- alert decisions

## Alert Engine

The current engine is vector-based.

- The first 10 calendar days after the first stored signal form a fixed baseline window.
- Each day gets a `daily centroid` from the mean of that day's stored embedding vectors.
- The baseline is a fixed `baseline centroid` built from the first 10 days.
- `daily_score` is the cosine distance between the `daily centroid` and the `baseline centroid`.
- `baseline_score` is the average baseline-day distance.
- A day is a deviation when `daily_score - baseline_score >= 0.2`.
- A push is recommended when there are 3 deviation days in the last 5 days.
- Cooldown is 5 days.

## Internal Eval

Run locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn safe_mind.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000/eval
```

The eval UI now uses the real configured models in strict mode for local inspection.

## Known Synthetic User

Primary OpenAI-backed seeded user:

```text
55555555-6666-4777-8888-999999999999
```

Expected push days:

- `2026-07-19`
- `2026-07-25`

These push days were preserved after the migration from `signal_strength`-based alerting to vector-based alerting.

## Useful Commands

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe scripts\seed_message_pipeline_demo_data.py
.\.venv\Scripts\python.exe scripts\rebuild_parent_alert_decisions.py
```

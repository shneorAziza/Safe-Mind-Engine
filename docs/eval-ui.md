# Internal Pipeline Eval UI

## Status

Implemented.

This is an internal testing UI, not part of the child app or parent app.
It can be removed later when the pipeline is stable.

## URL

Run the backend and open:

```text
http://127.0.0.1:8000/eval
```

## Purpose

The UI now has two jobs:

1. message-level pipeline inspection
2. user-level alert-engine inspection

The pipeline section lets us paste one or many messages and inspect the staged funnel:

```text
Raw Input
  -> Privacy
  -> Emotional Filter
  -> Psychological Analyzer
  -> Embedding + Vector/Metadata preview or storage
```

Each message is processed independently.
The display is grouped by stage, so every stage shows the messages that reached it.
Messages that are filtered out simply do not appear in later stages.

The alert dashboard section lets us:

- select a child user from the local DB
- inspect a 30-day window
- view fixed baseline days
- see daily vector distance, baseline distance, delta, deviation status, 3-of-5 count, push decision, and reason

## Defaults

By default:

- multiple messages are supported, one message per line
- embedding creation is enabled
- actual persistence is disabled
- the UI shows what would be stored in the vector DB and metadata
- the alert dashboard defaults to the last 30 days of the selected user
- raw/redacted/summary text appears only in local debug output

## API

The UI calls:

```http
POST /eval/run
GET /eval/alerts/users
GET /eval/alerts/timeline
```

`POST /eval/run` request shape:

```json
{
  "messages": ["message 1", "message 2"],
  "persist": false,
  "create_vector": true,
  "source_app": "eval-ui",
  "locale": "he"
}
```

`persist=false` means:

- create the embedding
- show vector preview and metadata
- do not write to SQLite

`create_vector=false` means:

- skip embedding entirely
- useful for faster privacy/filter/analyzer checks

`GET /eval/alerts/timeline` returns the daily alert timeline for one child user.
If `start_day` is omitted, the backend returns the last `days` window based on the latest stored signal for that user.

## Files

- [safe_mind/api/eval_ui.py](../safe_mind/api/eval_ui.py)
- [safe_mind/main.py](../safe_mind/main.py)
- [safe_mind/pipeline.py](../safe_mind/pipeline.py)
- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)

## Standard Test User

The current OpenAI-backed seeded user for dashboard inspection is:

```text
55555555-6666-4777-8888-999999999999
```

This user was generated from 30 synthetic messages that passed through the configured pipeline providers and currently produces push decisions on:

- `2026-07-19`
- `2026-07-25`

Under the current engine, the dashboard values should be interpreted as vector-drift metrics:

- `daily score` = cosine distance between that day's vector centroid and the fixed baseline centroid
- `baseline` = average baseline-day distance inside the first 10 days
- `delta` = `daily score - baseline`

## Privacy Note

The eval UI intentionally displays raw text, redacted text, and temporary summaries so we can debug the pipeline.

This must remain an internal local tool.

The vector store still does not store:

- raw text
- redacted text
- `summary_for_embedding`
- direct quotes

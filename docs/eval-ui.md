# Internal Eval UI

## Status

Implemented.

The Eval UI is an internal React page served by the backend. It is used to run large historical message datasets through the real configured SafeMind pipeline and inspect the resulting monitoring timeline, flags, and parent-alert decisions.

This is not part of the child app or parent app.

## URL

Run the backend and open:

```text
http://127.0.0.1:8000/eval
```

When `SAFE_MIND_EVAL_AUTH_PASSWORD` is configured, the page requires HTTP Basic Auth.

Before running Eval against MongoDB, verify the configured signal store:

```powershell
.\.venv\Scripts\python.exe scripts\check_mongodb_connection.py
```

## Main Workflow

Use **Dataset Simulation** for non-technical team evaluation.

The user provides:

- a CSV or JSON dataset of historical messages,
- an optional external user ID,
- a parent phone number for WhatsApp alerts,
- whether real WhatsApp alerts should be sent.

The backend then:

1. creates a real synthetic child user ID when one is not provided,
2. stores the external user mapping,
3. processes every message through the configured live pipeline,
4. persists daily signal scores into the configured signal store,
5. finalizes every day represented in the dataset,
6. returns the full dashboard timeline and per-day alert decisions.

## CSV Format

Recommended CSV:

```csv
timestamp,message
2026-01-01 20:00,"I felt calm today and talked with friends."
2026-01-02 20:00,"School was normal and I felt supported."
```

Required columns:

- `timestamp` - ISO-like date/time, for example `2026-01-17 22:00`.
- `message` - the message text to analyze.

Accepted aliases:

- timestamp: `timestamp`, `occurred_at`, `datetime`, or `date`
- message: `message`, `text`, or `content`

Optional columns:

- `source_app`
- `locale`

Naive timestamps are treated as UTC. Timestamps with timezone offsets are normalized to UTC.

## JSON Format

Eval also accepts either an array of messages or an object with a `messages` array:

```json
[
  {
    "timestamp": "2026-01-01 20:00",
    "message": "I felt calm today and talked with friends."
  }
]
```

## Parent Phone And WhatsApp

The `Parent phone` field is used only when `Send WhatsApp alerts for alert days` is enabled.

- Toggle off: Eval saves and displays alert decisions as dry-run results.
- Toggle on: Eval attempts real WhatsApp delivery for days where `should_send_push=true`.

Use an international phone number format, for example:

```text
+972501234567
```

If alert days appear but no WhatsApp is sent, check:

- the toggle is enabled,
- the phone number is present,
- the WhatsApp access token is valid,
- the template name and language match approved Meta templates.

## Alert-Triggering Content

The current alert engine is not triggered by one severe message alone.

The engine requires:

- baseline calibration from the first 10 signal days,
- daily deviations from that personal baseline,
- at least 3 different metrics,
- each of those metrics must repeat as a deviation for 3 consecutive days,
- all 3 metric streaks must be active on the same finalized day.

To intentionally trigger an alert, repeat the same concerning dimensions for 3 consecutive days. Good target dimensions are:

- loneliness,
- anxiety/stress,
- hopelessness,
- low self-worth.

Example 3-day alert-triggering pattern:

```csv
timestamp,message
2026-01-17 22:00,"I feel extremely lonely, very anxious, hopeless, and worthless."
2026-01-18 22:00,"The same feelings are still here: loneliness, intense anxiety, hopelessness, and low self-worth."
2026-01-19 22:00,"For the third day I feel deeply lonely, highly anxious, hopeless, and worthless."
```

To produce two expected alert days in one 40-day dataset:

- days 1-10: calm baseline,
- days 17-19: repeated loneliness/anxiety/hopelessness/self-worth streak,
- days 20-23: calmer gap,
- days 24-26: repeated concerning streak again,
- days 27-40: recovery or normal monitoring content.

Expected alert decision days for that pattern:

- `2026-01-19`
- `2026-01-26`

Model scoring can still move outcomes when OpenAI analysis is used. If no alert appears, inspect the dashboard's per-day metric scores and confirm the same 3 metrics are deviating for 3 consecutive days.

## API

The active Dataset Simulation UI calls:

```http
POST /eval/datasets/run
GET /eval/alerts/users
GET /eval/alerts/timeline
```

`POST /eval/datasets/run` request shape:

```json
{
  "dataset_text": "timestamp,message\n2026-01-01 20:00,\"I felt calm today.\"",
  "dataset_format": "csv",
  "child_user_id": null,
  "uid": "optional-external-user-id",
  "parent_phone": "+972501234567",
  "source_app": "eval-dataset",
  "locale": "he",
  "send_alerts": false
}
```

## Files

- [safe_mind/api/eval_ui.py](../safe_mind/api/eval_ui.py)
- [safe_mind/api/eval_ui_react.py](../safe_mind/api/eval_ui_react.py)
- [safe_mind/pipeline.py](../safe_mind/pipeline.py)
- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/alerts/finalization.py](../safe_mind/alerts/finalization.py)
- [safe_mind/storage/mongo_store.py](../safe_mind/storage/mongo_store.py)

## Privacy Note

The Eval UI intentionally accepts raw message text for internal testing.

It must remain an internal authenticated tool. Do not use real child messages unless the data handling and consent requirements for that environment have been approved.

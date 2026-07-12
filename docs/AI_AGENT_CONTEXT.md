# SafeMind AI Agent Context

This is the main context file for any AI agent or developer joining the SafeMind backend project.

Read this file before changing code. The older files in `docs/` are secondary references; this file is the current source of truth for product intent, runtime flow, storage rules, and pilot behavior.

## Product Goal

SafeMind is a backend pilot that registers parent/device clients, receives child-device text messages, removes private information, analyzes psychological signal metrics, builds a personal baseline, and raises an internal alert when the child shows a meaningful multi-day deviation from their own baseline.

The current system owns WhatsApp-code login, permanent app tokens, local parent phone storage, message ingestion, alert finalization, and WhatsApp template delivery.

## Current Message Ingestion Pipeline

```text
Incoming message
  -> app token + device id verification
  -> privacy redaction
  -> psychological analyzer
  -> daily metric aggregation
  -> acknowledgement to sender
```

There is no active first-stage emotional filter in the pilot flow. Every message is privacy-cleaned and then analyzed.
The realtime ingestion path does not send parent alerts immediately. Parent alert decisions are produced by a separate daily evaluation flow.

## What Happens Per Message

1. `POST /v1/app/messages` receives the frontend message batch with `Authorization: Bearer <token>` and a matching `deviceId`, or `POST /v1/ingest/messages` receives one internal message event.
2. The privacy redactor removes PII patterns before the model call.
3. The psychological analyzer returns numeric scores from 1 to 10.
4. The store updates exactly one daily record for the child and calendar day.
5. The ingestion endpoint acknowledges the accepted event. Alert decisions are not part of the sender-facing response.

The frontend auth flow stores `app_users` records with the permanent token hash, registered external device id, internal child/device ids, display name, and parent phone number.

## Daily Alert Evaluation

Parent alert decisions are evaluated once the calendar day has ended.

At `00:05` on a given date, the system evaluates the previous calendar day. For example, at `2026-06-25 00:05`, it evaluates the average scores for `2026-06-24`, compares that day to the child's baseline, updates the deviation/flag state, and only then decides whether a parent alert should be sent.

The outbound parent alert is a separate finalization flow: SafeMind reads the parent phone number from the local app user DB, then sends the WhatsApp template message. It is not coupled to the timing of incoming message requests.

Current handoff status, 2026-07-09:

- WhatsApp Cloud API direct sending has been tested successfully.
- Local `.env` is pointed at the approved Hebrew template `safe_mind_parent_alert`.
- Meta reports `safe_mind_parent_alert / APPROVED / he / MARKETING`.
- Meta reports `safe_mind_auth_code / APPROVED / he / AUTHENTICATION`.
- A real WhatsApp smoke send with the approved template succeeded.
- WhatsApp verification-code sending has been tested successfully.
- The final frontend ingestion endpoint is `POST /v1/app/messages`.
- Use [production-readiness.md](production-readiness.md) as the current checklist before production.

Deployment handoff update, 2026-07-12:

- The user is new to AWS and wants to continue deployment step-by-step, one completed step at a time.
- Docker Desktop is installed and open.
- AWS CLI v2 is installed and `aws --version` returned `aws-cli/2.35.21 Python/3.14.6 Windows/11 exe/AMD64`.
- The user signed in to AWS Console with root email/password and completed root MFA.
- The next AWS Console step is creating an IAM user named `safe-mind-deploy` for CLI deployment access.
- Active production model provider must stay OpenAI using `gpt-4o-mini`; do not switch the active deployment path to Bedrock/Claude.
- Bedrock support exists in code as an optional future provider, but it is not the current production configuration.

## Psychological Metrics

Each analyzed message returns:

```text
positive_emotion
negative_emotion
loneliness
anxiety_stress
hopelessness
self_worth_low
risk
```

Scores are on a 1 to 10 scale. Higher distress/risk metrics mean stronger concern. Lower `positive_emotion` can also count as a deviation when it drops meaningfully below baseline.

## Daily Aggregation

The database stores one document per user per day.

If a first message arrives for a day, the system creates a new daily record.

If another message arrives on the same day, the system updates the existing daily average:

```text
new_average = (old_average * old_message_count + new_message_score) / (old_message_count + 1)
```

No raw text, redacted text, model summary, quote, or evidence phrase is stored.

## Baseline and Alert Logic

The first 10 calendar days form the user's fixed baseline.

The baseline is a vector of metric averages, not one scalar number:

```text
baseline_scores = {
  positive_emotion,
  negative_emotion,
  loneliness,
  anxiety_stress,
  hopelessness,
  self_worth_low,
  risk
}
```

From day 11 onward, each daily metric vector is compared with the baseline vector.

A day is flagged when at least one metric deviates from baseline by its configured threshold. The system tracks a separate consecutive-day counter per metric, and sets `should_send_alert=true` only when at least 3 different metrics have each reached a 3-day consecutive deviation streak on the same finalized day.

The `alert_reason` is generated by deterministic code, not by the model. Example:

```text
בדידות +5.4 מהרגיל; חוסר תקווה +4.7 מהרגיל; סיכון +5.7 מהרגיל
```

This reason is only an explanation of metric differences. It is not a clinical diagnosis.

## MongoDB Storage

MongoDB Atlas is the current working DB for the pilot.

Set:

```env
SAFE_MIND_SIGNAL_STORE_PROVIDER=mongodb
SAFE_MIND_MONGODB_URI=...
SAFE_MIND_MONGODB_DATABASE=safe_mind
```

SQLite still exists as a local fallback for tests/offline development.

### `daily_signal_scores`

One document per child user per day.

Expected daily document fields:

```text
id
child_user_id
day
created_at
updated_at
message_count
scores
baseline_day_count
is_baseline_day
is_flagged
deviations_in_window
should_send_alert
alert_reason
```

### `message_events`

One idempotency document per received message event. This prevents retries with the same `messageId`/`event_id` from changing daily averages twice.

Expected fields:

```text
id
event_id
child_user_id
device_id
day
occurred_at
source_app
pipeline_version
status
daily_signal_score_id
created_at
updated_at
```

### `next_integration_mappings` Legacy

Legacy mapping for older backend-to-backend ingestion. The current frontend flow does not depend on Firebase/Next identity or parent-contact lookup; parent phone numbers live in `app_users`.

Expected fields:

```text
child_user_id
device_id
uid
external_device_id
created_at
updated_at
```

Do not add back these removed fields:

```text
daily_score
baseline_scores
baseline_score
delta
score_totals
pipeline_version
raw_text
redacted_text
summary
evidence
quotes
```

### `user_baselines`

One final baseline document per child user.

Expected fields:

```text
id
child_user_id
created_at
updated_at
baseline_start_day
baseline_end_day
baseline_day_count
scores
is_final
```

The baseline vector belongs here, not inside every daily record.

## Main Code Map

```text
safe_mind/
  main.py
  pipeline.py
  api/
    ingestion.py
    eval_ui.py
    eval_ui_react.py
    app_auth.py
    health.py
    metrics.py
    next_integration.py
  privacy/
    redactor.py
    models.py
  analysis/
    models.py
    bedrock_analyzer.py
    openai_analyzer.py
    heuristic_analyzer.py
    service.py
  signals/
    bedrock_emotional_filter.py
    openai_emotional_filter.py
    service.py
  alerts/
    engine.py
    finalization.py
    finalization_job.py
    models.py
  integrations/
    parent_contacts.py
    sms_verification.py
    whatsapp.py
  storage/
    factory.py
    models.py
    mongo_store.py
    vector_store.py
```

Important entry points:

- Runtime ingestion: `safe_mind/pipeline.py`
- Frontend auth and app endpoints: `safe_mind/api/app_auth.py`
- Internal ingestion endpoint: `safe_mind/api/ingestion.py`
- Legacy backend integration endpoint: `safe_mind/api/next_integration.py`
- Alert logic: `safe_mind/alerts/engine.py`
- Closed-day alert finalization: `safe_mind/alerts/finalization.py`
- Daily finalization job summary/WhatsApp orchestration: `safe_mind/alerts/finalization_job.py`
- WhatsApp verification delivery: `safe_mind/integrations/sms_verification.py`
- Outbound WhatsApp alerts: `safe_mind/integrations/whatsapp.py`
- Health/readiness endpoints: `safe_mind/api/health.py`
- In-process metrics endpoint: `safe_mind/api/metrics.py`
- Mongo storage: `safe_mind/storage/mongo_store.py`
- Eval dashboard: `safe_mind/api/eval_ui.py` and `safe_mind/api/eval_ui_react.py`

## Health and Metrics

Health endpoints:

```text
GET /health
GET /health/live
GET /health/ready
```

`/health/live` is a lightweight liveness check. `/health/ready` checks storage readiness and fails with `503` when storage is unavailable or production storage is misconfigured.

Metrics endpoint:

```text
GET /metrics
```

The metrics registry is intentionally simple and in-process for the pilot. It tracks counters and duration summaries for HTTP requests, app ingestion, finalization runs, and outbound WhatsApp sends. Metrics and logs must not include raw message text or redacted text.

## Internal Eval Dashboard

Run the server and open:

```text
http://127.0.0.1:8000/eval
```

The dashboard lets a developer or internal evaluator:

- run large CSV/JSON historical message datasets through the live pipeline,
- persist synthetic users and daily signal records into the configured signal store,
- list known child users,
- inspect alert timelines,
- verify baseline days, flagged days, alert days, reasons, and WhatsApp delivery status.

Dataset Eval expects at least `timestamp,message` columns. To intentionally trigger a parent alert, the dataset must create 3 different metric deviations that repeat for 3 consecutive days. Common test dimensions are loneliness, anxiety/stress, hopelessness, and low self-worth. The `Parent phone` field is used when `Send WhatsApp alerts for alert days` is enabled.

## Useful Scripts

Check MongoDB connectivity:

```powershell
.\.venv\Scripts\python.exe scripts\check_mongodb_connection.py
```

Finalize the previous closed day and optionally send outbound WhatsApp alerts:

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py --send-alerts
```

For manual testing of a specific closed day:

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py --target-day 2026-06-24 --send-alerts
```

Without `--send-alerts`, finalization saves decisions only and does not send WhatsApp.

List Meta WhatsApp templates:

```powershell
.\.venv\Scripts\python.exe scripts\list_whatsapp_templates.py
```

Send a direct WhatsApp smoke test:

```powershell
.\.venv\Scripts\python.exe scripts\send_whatsapp_smoke.py +972584853770
```

Seed the full synthetic message dataset through the real pipeline:

```powershell
.\.venv\Scripts\python.exe scripts\seed_message_pipeline_demo_data.py
```

Expected synthetic behavior:

```text
30 daily records
1 user baseline
alert days: 2026-07-19 and 2026-07-26
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Current expected result:

```text
70 passed
```

## Privacy Rules

Never store:

- raw message text,
- redacted message text,
- model summaries,
- direct quotes,
- evidence phrases,
- embeddings unless explicitly re-enabled and reviewed.

Allowed storage:

- pseudonymous user IDs,
- dates/timestamps,
- numeric daily metric averages,
- baseline metric averages,
- alert booleans/counts,
- deterministic alert reasons based on metric differences.

## Current Pilot Decisions To Preserve

1. MongoDB is the working pilot DB.
2. SQLite is only a fallback/test store.
3. No first-stage filtering in the active pilot flow.
4. Every message is privacy-redacted and then analyzed.
5. Each user/day has one daily metric document.
6. The first 10 days create a fixed vector baseline.
7. Day 11 onward is compared against that baseline.
8. Three consecutive finalized flagged days create an alert decision.
9. Alert reasons are deterministic metric deltas, not model-written prose.
10. The system does not make diagnoses and does not expose raw child text.
11. Incoming message requests acknowledge receipt only; parent alert sending is based on closed-day finalization.
12. In production, SQLite is rejected; `SAFE_MIND_SIGNAL_STORE_PROVIDER` must be `mongodb`.
13. End-to-end frontend tests must register through `/v1/auth/start` and `/v1/auth/verify`, then ingest through `/v1/app/messages` with the returned token and matching `deviceId`.
14. Active production inference uses OpenAI `gpt-4o-mini`; Bedrock is optional future support only.

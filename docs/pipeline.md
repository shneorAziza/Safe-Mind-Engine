# Current Pipeline

## Purpose

The backend supports message ingestion, privacy-first psychological scoring, daily aggregation, and closed-day alert finalization without a first-stage message filter.

```text
message
  -> app token + device id verification
  -> privacy redaction
  -> psychological signal analysis
  -> compact JSON signal scores
  -> signal-feature storage
  -> daily aggregation
  -> acknowledgement

closed-day finalization
  -> baseline/deviation evaluation
  -> parent alert decision
  -> parent phone lookup from local app user DB
  -> optional WhatsApp template send
```

SafeMind stores the parent phone number locally during WhatsApp-code registration/login. A second backend may still collect messages from devices, but the product auth, parent phone DB, analysis, and alert delivery live here.

Current handoff status, 2026-07-09:

- Direct WhatsApp Cloud API sending has been tested successfully.
- Local `.env` is pointed to the approved Hebrew template `safe_mind_parent_alert`.
- Meta reports `safe_mind_parent_alert / APPROVED / he / MARKETING`.
- Meta reports `safe_mind_auth_code / APPROVED / he / AUTHENTICATION`.
- A real WhatsApp smoke send with this template succeeded.
- WhatsApp verification-code sending has been tested successfully.

## Endpoint

Preferred product integration:

```http
POST /v1/app/messages
```

This endpoint accepts the permanent app token, the registered client `deviceId`, and a batch of messages. It returns an acknowledgement only; alert decisions are produced later by closed-day finalization.

Use this endpoint for frontend and end-to-end parent alert tests.

```http
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "deviceId": "device-unique-id-from-client",
  "messages": [
    {
      "text": "I feel overwhelmed and cannot sleep before tomorrow's exam.",
      "timestamp": 1780000000000
    }
  ]
}
```

Internal/debug endpoint:

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

No summary, evidence phrase, quote, raw text, or redacted text is stored for
real child-message ingestion.
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

Exception: the authenticated Eval simulator may attach `message_text` to the
matching `message_scores` entry for synthetic/manual Eval messages. App,
integration, and internal ingestion endpoints do not pass this field.

## Stage 4: Closed-Day Trend and Alert Decision

Files:

- [safe_mind/alerts/engine.py](../safe_mind/alerts/engine.py)
- [safe_mind/alerts/finalization.py](../safe_mind/alerts/finalization.py)
- [safe_mind/alerts/finalization_job.py](../safe_mind/alerts/finalization_job.py)
- [safe_mind/alerts/models.py](../safe_mind/alerts/models.py)

After the calendar day closes, the finalization flow evaluates the child's alert state:

- fixed baseline from the first 10 signal days; empty calendar days do not count
- daily vector from that day's compact psychological scores
- baseline vector from the average baseline-day scores
- per-metric deviation thresholds
- alert gate of `3 different metrics that each reached a 3-day consecutive deviation streak on the same finalized day`

The output is an internal `ParentAlertDecision`.

## What the Endpoint Returns

The ingestion response includes:

- privacy summary
- signal features
- storage summary

The frontend message-batch response is acknowledgement-only and does not include alert decisions.

## Daily Finalization Script

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py --send-alerts
```

At `00:05`, this evaluates the previous calendar day and sends WhatsApp alerts only for finalized parent-alert decisions.

Without `--send-alerts`, the script only saves `ParentAlertDecision` records. It does not send WhatsApp.

For a manual test of a known alert day:

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py --target-day 2026-07-19 --send-alerts
```

# Production Readiness Handoff

Last updated: 2026-07-09

Deployment handoff update: 2026-07-12

This file captures the current handoff state for continuing tomorrow.

## What Is Ready

- MongoDB pilot storage is configured in local `.env`.
- WhatsApp Cloud API credentials are configured locally.
- The configured WhatsApp sender `phone_number_id` successfully sent a real message through Meta.
- The approved Hebrew parent alert template is configured and has successfully sent a real WhatsApp smoke message:

```env
SAFE_MIND_WHATSAPP_TEMPLATE_NAME=safe_mind_parent_alert
SAFE_MIND_WHATSAPP_TEMPLATE_LANGUAGE=he
```

- Meta currently reports:

```text
safe_mind_parent_alert / APPROVED / he / MARKETING
safe_mind_auth_code / APPROVED / he / AUTHENTICATION
```

Template body:

```text
שלום, זוהתה מגמה מתמשכת שמומלץ לבדוק מול הילד/ה.

כדאי ליצור קשר, לשאול לשלומו/ה, ולוודא שהכול בסדר.
```

Footer:

```text
Safe Mind
```

## Current Production Flow

The backend owns registration/login, parent phone storage, message ingestion, alert logic, and WhatsApp delivery.

- `POST /v1/auth/start` sends the WhatsApp verification code.
- `POST /v1/auth/verify` verifies the code, creates/updates `app_users`, and returns the permanent token.
- `GET /v1/me` and `PATCH /v1/me` use the permanent token.
- `POST /v1/app/messages` is the final frontend message endpoint. It requires `Authorization: Bearer <token>` and a matching `deviceId` in the JSON body.

The parent phone number is stored locally in the SafeMind DB, not fetched from a separate Next/Firebase parent-contact service.

## Finalizer Reminder

Ingestion never sends parent WhatsApp alerts immediately. Parent alerts are sent only by closed-day finalization.

This saves decisions only:

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py
```

This saves decisions and sends WhatsApp alerts when `should_send_push=true`:

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py --send-alerts
```

For testing a known synthetic alert day:

```powershell
.\.venv\Scripts\python.exe scripts\finalize_previous_day.py --target-day 2026-07-19 --send-alerts
```

## End-to-End Test Plan

1. Call `POST /v1/auth/start` with `deviceId`, `name`, and parent `phoneNumber`.
2. Confirm the tester phone receives the WhatsApp auth code.
3. Call `POST /v1/auth/verify` and store the returned permanent token.
4. Call `GET /v1/me` with the token and confirm the registered user is returned.
5. Send messages through `POST /v1/app/messages` with `Authorization: Bearer <token>` and the same `deviceId`.
6. Confirm the response reports accepted/stored events.
7. Finalize an alert day with `--send-alerts`.
8. Confirm the finalizer summary shows `whatsapp_sent > 0`.
9. Confirm the tester phone receives a WhatsApp parent alert.

## Useful WhatsApp Commands

List current Meta templates:

```powershell
.\.venv\Scripts\python.exe scripts\list_whatsapp_templates.py
```

Send a direct WhatsApp smoke test to a phone number:

```powershell
.\.venv\Scripts\python.exe scripts\send_whatsapp_smoke.py +972584853770
```

Create the Hebrew template again if needed:

```powershell
.\.venv\Scripts\python.exe scripts\create_whatsapp_template.py
```

Create the Hebrew authentication-code template again if needed:

```powershell
.\.venv\Scripts\python.exe scripts\create_whatsapp_verification_template.py
```

## Before Production

- Confirm the production WhatsApp templates remain approved:
  `safe_mind_parent_alert` and `safe_mind_auth_code`.
- Configure MongoDB, WhatsApp, OpenAI, Eval Basic Auth, and production secret values.
- Keep `/eval` exposed only on the API Lambda and protected with `SAFE_MIND_EVAL_AUTH_PASSWORD`.
- Keep the active model path on OpenAI `gpt-4o-mini`; Bedrock support is optional future code only.
- Continue AWS deployment guidance from IAM user creation: create `safe-mind-deploy`, no Console access, attach `AdministratorAccess` for the first deployment, then create a CLI access key.
- Run one end-to-end auth and message-ingestion test through `/v1/auth/start`, `/v1/auth/verify`, and `/v1/app/messages`.
- Schedule the finalizer with `--send-alerts`.
- Decide finalizer timezone. The code currently finalizes the previous UTC day by default.
- Store production secrets in AWS Secrets Manager or the selected production secret store.
- Rotate any development tokens before production if they were shared in chat or local logs.

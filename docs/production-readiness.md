# Production Readiness Handoff

Last updated: 2026-07-09

Deployment handoff update: 2026-07-12

This file captures the current handoff state for continuing tomorrow.

Important handoff note, 2026-07-12 evening: AWS production is live, but the latest
local code changes have not been deployed yet. The public Lambda still runs the
previous ECR image until the deploy steps in `README.md` are executed.

## Current AWS Production State

- Public production API base URL:

```text
https://qi86pazbij.execute-api.us-east-1.amazonaws.com
```

- AWS region: `us-east-1`.
- AWS CLI profile: `safe-mind-deploy`.
- ECR repository: `415019015823.dkr.ecr.us-east-1.amazonaws.com/safe-mind-api`.
- Lambda function: `safe-mind-api`.
- Lambda role: `safe-mind-lambda-role`.
- Lambda image tag: `latest`.
- Lambda memory/timeout: `1024 MB`, `30 seconds`.
- `GET /health/live` works from the public API URL.
- `GET /health/ready` works from the public API URL and reports MongoDB storage `ok`.
- `/eval` is enabled and protected with Basic Auth (`safemind` plus `SAFE_MIND_EVAL_AUTH_PASSWORD`).
- A Lambda Function URL was tested first, but it remapped the `WWW-Authenticate` header and did not reliably open a browser Basic Auth prompt. API Gateway HTTP API is the preferred public URL.

## Local Changes Not Yet Deployed To AWS

These are implemented and tested locally, but are not live in AWS production yet:

- Eval timeline baseline display now counts baseline by signal days, not empty calendar days.
- Dataset Simulation creates a fresh synthetic test user for every run, so a pasted CSV does not merge into the previously selected dashboard user.
- React Eval UI was reorganized for easier non-technical testing:
  - Dataset Simulation appears before existing-user dashboard loading.
  - Run is styled green; Dashboard is styled blue; tabs match those colors.
  - A large loading animation appears in the main result area during dataset runs and dashboard loads.
  - The AI prompt block is copyable and styled like a code snippet.
  - Run results use compact clickable rows with expandable details, like the existing dashboard timeline.
  - Run guidance explains that `Max streak = 3` is not sufficient unless at least 3 different metrics each have a 3-day streak on the same day.
- README now includes the production redeploy command sequence.
- Local verification: `.\.venv\Scripts\python.exe -m pytest` returned `71 passed`.

Before deploying tomorrow, run the test suite again, then build and push the
Lambda image and run `aws lambda update-function-code`.

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
- MongoDB, WhatsApp, OpenAI, Eval Basic Auth, and production secret values are configured on the API Lambda.
- Keep `/eval` exposed only on the API Lambda/API Gateway and protected with `SAFE_MIND_EVAL_AUTH_PASSWORD`.
- Keep the active model path on OpenAI `gpt-4o-mini`; Bedrock support is optional future code only.
- Send the frontend engineer the API base URL, but do not send `SAFE_MIND_INTEGRATION_API_TOKEN` for Android client work.
- Run one end-to-end auth and message-ingestion test through the public API Gateway URL:
  `/v1/auth/start`, `/v1/auth/verify`, `/v1/me`, and `/v1/app/messages`.
- Schedule the finalizer with `--send-alerts`.
- Decide finalizer timezone. The code currently finalizes the previous UTC day by default.
- Store production secrets in AWS Secrets Manager or the selected production secret store.
- Rotate any development tokens before production if they were shared in chat or local logs.
- Reduce `safe-mind-deploy` from broad first-deployment admin permissions once the deployment is stable.

## Token Handoff Note

The Android frontend should not use `SAFE_MIND_INTEGRATION_API_TOKEN`.

- Android flow: `POST /v1/auth/start` -> `POST /v1/auth/verify` -> store returned per-user token -> use `Authorization: Bearer <token>`.
- Message endpoint for Android: `POST /v1/app/messages`.
- `SAFE_MIND_INTEGRATION_API_TOKEN` is only for the legacy/internal `POST /v1/integrations/next/messages` endpoint and should remain server-side.

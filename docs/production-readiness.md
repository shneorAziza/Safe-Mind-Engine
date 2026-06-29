# Production Readiness Handoff

Last updated: 2026-06-30

This file captures the current handoff state for continuing tomorrow.

## What Is Ready

- MongoDB pilot storage is configured in local `.env`.
- WhatsApp Cloud API credentials are configured locally.
- The configured WhatsApp sender `phone_number_id` successfully sent a real message through Meta.
- A temporary approved template is configured for pipeline smoke tests:

```env
SAFE_MIND_WHATSAPP_TEMPLATE_NAME=hello_world
SAFE_MIND_WHATSAPP_TEMPLATE_LANGUAGE=en_US
```

- The real Safe Mind Hebrew template was created in Meta:

```text
safe_mind_parent_alert / PENDING / he / UTILITY
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

When Meta changes it to `APPROVED`, switch `.env` back to:

```env
SAFE_MIND_WHATSAPP_TEMPLATE_NAME=safe_mind_parent_alert
SAFE_MIND_WHATSAPP_TEMPLATE_LANGUAGE=he
```

## What Is Not Yet Fully Connected

The WhatsApp send path works, but full automatic parent alert delivery still needs parent contact lookup configuration:

```env
SAFE_MIND_PARENT_CONTACT_URL_TEMPLATE=
SAFE_MIND_PARENT_CONTACT_TOKEN=
```

Use a Next/Firebase backend URL:

```env
SAFE_MIND_PARENT_CONTACT_URL_TEMPLATE=http://localhost:3000/api/internal/parent-contact/{uid}
```

or production:

```env
SAFE_MIND_PARENT_CONTACT_URL_TEMPLATE=https://YOUR-DOMAIN.com/api/internal/parent-contact/{uid}
```

The same shared secret must be configured on both sides:

```env
# SafeMind backend
SAFE_MIND_PARENT_CONTACT_TOKEN=<shared-secret>

# Next/Firebase backend
SAFE_MIND_INTERNAL_API_TOKEN=<same-shared-secret>
```

Firestore must contain the parent phone on `users/{uid}`. Prefer:

```text
parentPhone: "+972584853770"
```

The Next endpoint also accepts these string fields: `parent_phone`, `parentPhoneNumber`, `parentWhatsapp`, `parentWhatsApp`, `phone`, or `phoneNumber`.

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

1. Run or deploy the Next/Firebase backend parent-contact endpoint.
2. Put the shared token into both `SAFE_MIND_PARENT_CONTACT_TOKEN` and `SAFE_MIND_INTERNAL_API_TOKEN`.
3. Create or choose a Firebase test user.
4. Set `users/{uid}.parentPhone` in Firestore to the tester phone number.
5. Ingest the dataset through `POST /v1/integrations/next/messages`, not the direct internal ingest endpoint, so SafeMind stores the Firebase `uid` mapping.
6. Finalize an alert day with `--send-alerts`.
7. Confirm the finalizer summary shows `whatsapp_sent > 0`.
8. Confirm the tester phone receives a WhatsApp message.

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

## Before Production

- Approve or replace the Hebrew WhatsApp template.
- Configure parent contact lookup secrets in the production environment.
- Verify the Next/Firebase parent-contact endpoint works against real Firestore data.
- Run one end-to-end test through `/v1/integrations/next/messages`.
- Schedule the finalizer with `--send-alerts`.
- Decide finalizer timezone. The code currently finalizes the previous UTC day by default.
- Store production secrets in AWS Secrets Manager or the selected production secret store.
- Rotate any development tokens before production if they were shared in chat or local logs.

# Safe Mind Frontend API Contract

This document describes the endpoints the frontend should use to communicate with the Safe Mind backend.

## Base URL

Local testing:

```text
http://127.0.0.1:8000
```

Production:

```text
<production-api-url>
```

All request and response bodies are JSON.

## Authentication Model

The frontend receives a permanent token after phone verification.

For every authenticated request, send:

```http
Authorization: Bearer <token>
Content-Type: application/json
```

The token should be stored by the frontend and reused for future requests.

## 1. Start Registration/Login

Sends a WhatsApp verification code to the parent phone number.

```http
POST /v1/auth/start
```

Request:

```json
{
  "deviceId": "device-unique-id-from-client",
  "name": "Parent Or Child Name",
  "phoneNumber": "+972584853770"
}
```

Response:

```json
{
  "challengeId": "5c7b0d66-4fd4-4fa4-9fd5-4ff1f0031d0c",
  "status": "verification_sent",
  "expiresAt": "2026-07-09T16:30:00Z"
}
```

Notes:

- The verification code is sent via WhatsApp.
- The code is not returned in the API response.
- `challengeId` is required for the verify step.
- `deviceId` must remain stable for this device.

Common errors:

```json
{
  "detail": "Verification code delivery failed. ..."
}
```

This means WhatsApp delivery failed. The frontend should show a retry/error state.

## 2. Verify Code And Receive Token

Completes login/registration and returns the permanent API token.

```http
POST /v1/auth/verify
```

Request:

```json
{
  "challengeId": "5c7b0d66-4fd4-4fa4-9fd5-4ff1f0031d0c",
  "phoneNumber": "+972584853770",
  "code": "123456"
}
```

Response:

```json
{
  "childUserId": "778703f1-8701-540c-af16-0fdbeb965e69",
  "deviceId": "c371f115-e27a-53b2-81fb-51fd608cca70",
  "externalDeviceId": "device-unique-id-from-client",
  "name": "Parent Or Child Name",
  "phoneNumber": "+972584853770",
  "token": "permanent-token-value"
}
```

Frontend storage:

- Store `token`.
- Store `externalDeviceId` or keep using the same local device id.
- Use the token in all authenticated requests.

Common errors:

```json
{
  "detail": "Invalid or expired verification code."
}
```

## 3. Get Current User

Returns the authenticated user.

```http
GET /v1/me
Authorization: Bearer <token>
```

Response:

```json
{
  "childUserId": "778703f1-8701-540c-af16-0fdbeb965e69",
  "deviceId": "c371f115-e27a-53b2-81fb-51fd608cca70",
  "externalDeviceId": "device-unique-id-from-client",
  "name": "Parent Or Child Name",
  "phoneNumber": "+972584853770"
}
```

Common errors:

```http
401 Unauthorized
```

## 4. Update User Name

Updates the user display name.

```http
PATCH /v1/me
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "name": "Updated Name"
}
```

Response:

```json
{
  "childUserId": "778703f1-8701-540c-af16-0fdbeb965e69",
  "deviceId": "c371f115-e27a-53b2-81fb-51fd608cca70",
  "externalDeviceId": "device-unique-id-from-client",
  "name": "Updated Name",
  "phoneNumber": "+972584853770"
}
```

## 5. Send Messages Batch

This is the final frontend endpoint for sending messages to the backend.

```http
POST /v1/app/messages
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "deviceId": "device-unique-id-from-client",
  "messages": [
    {
      "text": "I've been feeling really overwhelmed with school lately",
      "timestamp": 1752019200000
    },
    {
      "text": "That sounds really hard. Do you want to talk about what's been the most stressful?",
      "timestamp": 1752019205000
    },
    {
      "text": "I guess I just feel like nobody understands what I'm going through",
      "timestamp": 1752019260000
    }
  ]
}
```

Extended message fields:

```json
{
  "deviceId": "device-unique-id-from-client",
  "messages": [
    {
      "messageId": "local-message-id-001",
      "occurredAt": "2026-07-09T10:00:00Z",
      "sourceType": "notification",
      "sourceApp": "com.whatsapp",
      "text": "I feel overwhelmed and alone today.",
      "locale": "en"
    }
  ]
}
```

Response:

```json
{
  "received": 3,
  "accepted": 3,
  "events": [
    {
      "messageId": null,
      "eventId": "bccad0ca-b345-5eca-a181-4d4eac198994",
      "status": "accepted",
      "storedSignal": {
        "stored": true,
        "signalId": "5b4ccb62-2887-44a3-8cdf-1995834ca48c",
        "dailyScoreId": "0702ad9b-887b-4e6f-91e2-6c1e1f1387d3"
      }
    },
    {
      "messageId": null,
      "eventId": "5dbbb7f0-0eb6-53c2-92a4-1224a0a1dfb2",
      "status": "accepted",
      "storedSignal": {
        "stored": true,
        "signalId": "8f5f0478-7797-41a9-8c7f-4d32f0ddf94c",
        "dailyScoreId": "0702ad9b-887b-4e6f-91e2-6c1e1f1387d3"
      }
    }
  ]
}
```

Field rules:

- `deviceId`: required. It must match the device id used during registration/login. The token identifies the user; `deviceId` verifies that the messages are coming from the registered device.
- `messages`: 1 to 100 messages per request.
- `text`: required, 1 to 10000 characters.
- `timestamp`: required unless `occurredAt` is sent. Unix timestamp in milliseconds.
- `occurredAt`: optional alternative to `timestamp`. ISO 8601 datetime.
- `messageId`: optional but recommended. It should be stable and unique per message on the device.
- `sourceType`: optional. Defaults to `notification`. Valid values:
  - `notification`
  - `share_intent`
  - `accessibility`
  - `manual`
- `sourceApp`: optional app/package/source name.
- `locale`: optional, for example `he` or `en`.

Idempotency:

- If `messageId` is provided and the same message is sent again for the same user/device, the backend returns the same stable `eventId`.
- If `messageId` is not provided, the backend builds a stable id from `timestamp`/`occurredAt` and `text`.
- Duplicate sends should not double-count the message in the database.

Common errors:

```http
401 Unauthorized
```

Missing or invalid token.

```http
403 Forbidden
```

`deviceId` does not match the authenticated user.

```http
422 Unprocessable Entity
```

Invalid request body, missing fields, too many messages, invalid timestamp, etc.

## 6. Health Check

Useful for connectivity checks.

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "safe_mind"
}
```

Readiness check:

```http
GET /health/ready
```

Response:

```json
{
  "status": "ready",
  "service": "safe_mind",
  "checks": {
    "env": "production",
    "signal_store_provider": "mongodb",
    "storage": "ok"
  }
}
```

## Frontend Flow Summary

1. Call `POST /v1/auth/start`.
2. User receives code in WhatsApp.
3. Call `POST /v1/auth/verify` with the code.
4. Store the returned `token`.
5. Use `Authorization: Bearer <token>` for all future calls.
6. Send messages with `POST /v1/app/messages`.
7. Use `PATCH /v1/me` if the user changes name.

## Endpoints Not Intended For Frontend

These endpoints exist for internal/backend/debug use and should not be used by the frontend app:

```text
POST /v1/ingest/messages
POST /v1/integrations/next/messages
GET /eval
POST /eval/run
POST /eval/datasets/run
GET /metrics
```

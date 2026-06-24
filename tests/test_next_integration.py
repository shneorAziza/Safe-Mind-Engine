from fastapi.testclient import TestClient

from safe_mind.core.metrics import metrics
from safe_mind.main import app


def test_next_integration_accepts_firebase_shaped_batch(monkeypatch) -> None:
    metrics.reset()
    monkeypatch.setattr("safe_mind.core.config.settings.env", "local")
    monkeypatch.setattr("safe_mind.core.config.settings.integration_api_token", None)
    monkeypatch.setattr("safe_mind.core.config.settings.persist_signals", False)
    monkeypatch.setattr("safe_mind.core.config.settings.psychological_analyzer_provider", "heuristic")
    client = TestClient(app)

    response = client.post(
        "/v1/integrations/next/messages",
        json={
            "uid": "firebase-parent-user",
            "deviceId": "firestore-device-id",
            "messages": [
                {
                    "messageId": "device-message-1",
                    "text": "I feel overwhelmed today.",
                    "timestamp": 1780000000000,
                    "sourceApp": "com.openai.chatgpt",
                    "locale": "en",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["received"] == 1
    assert body["accepted"] == 1
    assert body["childUserId"]
    assert body["deviceId"]
    assert body["events"][0]["messageId"] == "device-message-1"
    assert body["events"][0]["eventId"]
    assert body["events"][0]["status"] == "accepted"
    assert "shouldSendAlert" not in body["events"][0]
    assert "signalFeatures" not in body["events"][0]
    assert "alertDecision" not in body["events"][0]
    snapshot = metrics.snapshot()
    assert snapshot["counters"]["next_ingest.requests.total"] == 1
    assert snapshot["counters"]["next_ingest.messages.received"] == 1
    assert snapshot["counters"]["next_ingest.messages.accepted"] == 1


def test_next_integration_uses_stable_event_id_for_retries(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.integration_api_token", None)
    monkeypatch.setattr("safe_mind.core.config.settings.persist_signals", False)
    monkeypatch.setattr("safe_mind.core.config.settings.psychological_analyzer_provider", "heuristic")
    client = TestClient(app)
    payload = {
        "uid": "firebase-parent-user",
        "deviceId": "firestore-device-id",
        "messages": [
            {
                "messageId": "same-device-message",
                "text": "I feel stressed.",
                "timestamp": 1780000000000,
            }
        ],
    }

    first = client.post("/v1/integrations/next/messages", json=payload)
    second = client.post("/v1/integrations/next/messages", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["events"][0]["eventId"] == second.json()["events"][0]["eventId"]


def test_next_integration_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.integration_api_token", "internal-secret")
    monkeypatch.setattr("safe_mind.core.config.settings.persist_signals", False)
    client = TestClient(app)
    payload = {
        "uid": "firebase-parent-user",
        "deviceId": "firestore-device-id",
        "messages": [{"messageId": "m1", "text": "hello", "timestamp": 1780000000000}],
    }

    unauthorized = client.post("/v1/integrations/next/messages", json=payload)
    authorized = client.post(
        "/v1/integrations/next/messages",
        json=payload,
        headers={"Authorization": "Bearer internal-secret"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_next_integration_fails_closed_in_production_without_token(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.env", "production")
    monkeypatch.setattr("safe_mind.core.config.settings.integration_api_token", None)
    client = TestClient(app)

    response = client.post(
        "/v1/integrations/next/messages",
        json={
            "uid": "firebase-parent-user",
            "deviceId": "firestore-device-id",
            "messages": [{"messageId": "m1", "text": "hello", "timestamp": 1780000000000}],
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Integration API token is not configured."

from fastapi.testclient import TestClient
from pydantic import BaseModel

from safe_mind.main import app
from safe_mind.storage.factory import _get_signal_store


class FakeSendResult(BaseModel):
    sent: bool
    skipped: bool = False
    error: str | None = None


def test_auth_verify_issues_token_and_allows_name_update(monkeypatch, tmp_path) -> None:
    _configure_sqlite_store(monkeypatch, tmp_path)
    monkeypatch.setattr("safe_mind.api.app_auth._verification_code", lambda: "123456")
    monkeypatch.setattr(
        "safe_mind.api.app_auth.send_verification_code",
        lambda **kwargs: FakeSendResult(sent=True),
    )
    client = TestClient(app)

    start = client.post(
        "/v1/auth/start",
        json={
            "deviceId": "android-device-1",
            "name": "Original Name",
            "phoneNumber": "+972 50-123-4567",
        },
    )
    assert start.status_code == 200
    challenge = start.json()
    assert challenge["challengeId"]
    assert "verificationCode" not in challenge

    verify = client.post(
        "/v1/auth/verify",
        json={
            "challengeId": challenge["challengeId"],
            "phoneNumber": "+972501234567",
            "code": "123456",
        },
    )

    assert verify.status_code == 200
    body = verify.json()
    assert body["token"]
    assert body["name"] == "Original Name"
    assert body["phoneNumber"] == "+972501234567"

    updated = client.patch(
        "/v1/me",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {body['token']}"},
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Name"


def test_app_messages_require_token_and_use_authenticated_user(monkeypatch, tmp_path) -> None:
    _configure_sqlite_store(monkeypatch, tmp_path)
    monkeypatch.setattr("safe_mind.api.app_auth._verification_code", lambda: "123456")
    monkeypatch.setattr(
        "safe_mind.api.app_auth.send_verification_code",
        lambda **kwargs: FakeSendResult(sent=True),
    )
    monkeypatch.setattr("safe_mind.core.config.settings.persist_signals", False)
    monkeypatch.setattr("safe_mind.core.config.settings.psychological_analyzer_provider", "heuristic")
    client = TestClient(app)
    start = client.post(
        "/v1/auth/start",
        json={"deviceId": "android-device-1", "name": "Child", "phoneNumber": "+972501234567"},
    )
    verify = client.post(
        "/v1/auth/verify",
        json={
            "challengeId": start.json()["challengeId"],
            "phoneNumber": "+972501234567",
            "code": "123456",
        },
    )
    token = verify.json()["token"]

    unauthorized = client.post(
        "/v1/app/messages",
        json={
            "deviceId": "android-device-1",
            "messages": [
                {
                    "messageId": "device-message-1",
                    "occurredAt": "2026-07-09T10:00:00Z",
                    "sourceType": "notification",
                    "text": "I feel overwhelmed today.",
                }
            ],
        },
    )
    authorized = client.post(
        "/v1/app/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "deviceId": "android-device-1",
            "messages": [
                {
                    "messageId": "device-message-1",
                    "occurredAt": "2026-07-09T10:00:00Z",
                    "sourceType": "notification",
                    "sourceApp": "com.chat",
                    "text": "I feel overwhelmed today.",
                },
                {
                    "messageId": "device-message-2",
                    "occurredAt": "2026-07-09T10:01:00Z",
                    "sourceType": "notification",
                    "sourceApp": "com.chat",
                    "text": "Nobody understands me today.",
                },
            ],
        },
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 202
    body = authorized.json()
    assert body["received"] == 2
    assert body["accepted"] == 2
    assert body["events"][0]["messageId"] == "device-message-1"
    assert body["events"][0]["eventId"]
    assert body["events"][0]["status"] == "accepted"
    assert body["events"][0]["storedSignal"] == {
        "stored": False,
        "signalId": None,
        "dailyScoreId": None,
    }
    assert "signal_features" not in body
    assert "privacy" not in body
    assert "alert_decision" not in body
    assert "embeddingModel" not in body["events"][0]["storedSignal"]


def test_app_messages_rejects_wrong_device_id(monkeypatch, tmp_path) -> None:
    _configure_sqlite_store(monkeypatch, tmp_path)
    monkeypatch.setattr("safe_mind.api.app_auth._verification_code", lambda: "123456")
    monkeypatch.setattr(
        "safe_mind.api.app_auth.send_verification_code",
        lambda **kwargs: FakeSendResult(sent=True),
    )
    client = TestClient(app)
    start = client.post(
        "/v1/auth/start",
        json={"deviceId": "android-device-1", "name": "Child", "phoneNumber": "+972501234567"},
    )
    verify = client.post(
        "/v1/auth/verify",
        json={
            "challengeId": start.json()["challengeId"],
            "phoneNumber": "+972501234567",
            "code": "123456",
        },
    )

    response = client.post(
        "/v1/app/messages",
        headers={"Authorization": f"Bearer {verify.json()['token']}"},
        json={
            "deviceId": "different-device",
            "messages": [
                {
                    "messageId": "device-message-1",
                    "occurredAt": "2026-07-09T10:00:00Z",
                    "sourceType": "notification",
                    "text": "I feel overwhelmed today.",
                }
            ],
        },
    )

    assert response.status_code == 403


def test_app_messages_accepts_frontend_minimal_batch_shape(monkeypatch, tmp_path) -> None:
    _configure_sqlite_store(monkeypatch, tmp_path)
    monkeypatch.setattr("safe_mind.api.app_auth._verification_code", lambda: "123456")
    monkeypatch.setattr(
        "safe_mind.api.app_auth.send_verification_code",
        lambda **kwargs: FakeSendResult(sent=True),
    )
    monkeypatch.setattr("safe_mind.core.config.settings.persist_signals", False)
    monkeypatch.setattr("safe_mind.core.config.settings.psychological_analyzer_provider", "heuristic")
    client = TestClient(app)
    start = client.post(
        "/v1/auth/start",
        json={"deviceId": "android-device-1", "name": "Child", "phoneNumber": "+972501234567"},
    )
    verify = client.post(
        "/v1/auth/verify",
        json={
            "challengeId": start.json()["challengeId"],
            "phoneNumber": "+972501234567",
            "code": "123456",
        },
    )

    response = client.post(
        "/v1/app/messages",
        headers={"Authorization": f"Bearer {verify.json()['token']}"},
        json={
            "deviceId": "android-device-1",
            "messages": [
                {
                    "text": "I've been feeling really overwhelmed with school lately",
                    "timestamp": 1752019200000,
                },
                {
                    "text": "That sounds really hard. Do you want to talk about what's been the most stressful?",
                    "timestamp": 1752019205000,
                },
                {
                    "text": "I guess I just feel like nobody understands what I'm going through",
                    "timestamp": 1752019260000,
                },
            ]
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["received"] == 3
    assert body["accepted"] == 3
    assert body["events"][0]["messageId"] is None
    assert body["events"][0]["eventId"]


def test_app_messages_requires_device_id(monkeypatch, tmp_path) -> None:
    _configure_sqlite_store(monkeypatch, tmp_path)
    monkeypatch.setattr("safe_mind.api.app_auth._verification_code", lambda: "123456")
    monkeypatch.setattr(
        "safe_mind.api.app_auth.send_verification_code",
        lambda **kwargs: FakeSendResult(sent=True),
    )
    client = TestClient(app)
    start = client.post(
        "/v1/auth/start",
        json={"deviceId": "android-device-1", "name": "Child", "phoneNumber": "+972501234567"},
    )
    verify = client.post(
        "/v1/auth/verify",
        json={
            "challengeId": start.json()["challengeId"],
            "phoneNumber": "+972501234567",
            "code": "123456",
        },
    )

    response = client.post(
        "/v1/app/messages",
        headers={"Authorization": f"Bearer {verify.json()['token']}"},
        json={
            "messages": [
                {
                    "text": "I've been feeling really overwhelmed with school lately",
                    "timestamp": 1752019200000,
                }
            ]
        },
    )

    assert response.status_code == 422


def test_auth_start_fails_when_verification_delivery_fails(monkeypatch, tmp_path) -> None:
    _configure_sqlite_store(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "safe_mind.api.app_auth.send_verification_code",
        lambda **kwargs: FakeSendResult(sent=False, error="template_missing"),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/auth/start",
        json={"deviceId": "android-device-1", "name": "Child", "phoneNumber": "+972501234567"},
    )

    assert response.status_code == 503
    assert "template_missing" in response.json()["detail"]


def _configure_sqlite_store(monkeypatch, tmp_path) -> None:
    _get_signal_store.cache_clear()
    monkeypatch.setattr("safe_mind.core.config.settings.env", "local")
    monkeypatch.setattr("safe_mind.core.config.settings.signal_store_provider", "sqlite")
    monkeypatch.setattr(
        "safe_mind.core.config.settings.signal_db_path",
        str(tmp_path / "signals.sqlite3"),
    )

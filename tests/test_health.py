from fastapi.testclient import TestClient

from safe_mind.api import health
from safe_mind.main import app
from safe_mind.storage.factory import _get_signal_store


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "safe_mind"}


def test_liveness_check() -> None:
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "safe_mind"}


def test_readiness_check_reports_storage_ok(monkeypatch, tmp_path) -> None:
    _get_signal_store.cache_clear()
    monkeypatch.setattr("safe_mind.core.config.settings.env", "local")
    monkeypatch.setattr("safe_mind.core.config.settings.signal_store_provider", "sqlite")
    monkeypatch.setattr("safe_mind.core.config.settings.signal_db_path", str(tmp_path / "signals.sqlite3"))
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["storage"] == "ok"


def test_readiness_check_fails_when_storage_ping_fails(monkeypatch) -> None:
    class BrokenStore:
        def ping(self) -> None:
            raise RuntimeError("db unavailable")

    monkeypatch.setattr(health, "get_signal_store", lambda: BrokenStore())
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["storage"]["status"] == "error"
    assert detail["storage"]["message"] == "db unavailable"

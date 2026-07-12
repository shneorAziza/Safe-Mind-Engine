from fastapi.testclient import TestClient

import safe_mind.api.eval_ui as eval_ui
from safe_mind.analysis.models import PsychologicalScores, SignalFeatures
from safe_mind.main import app, create_app
from safe_mind.storage.models import DailySignalRecord
from safe_mind.storage.vector_store import SQLiteVectorStore
from uuid import UUID, uuid4
from datetime import UTC, datetime

import pytest


@pytest.fixture(autouse=True)
def _default_eval_auth_settings(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.env", "local")
    monkeypatch.setattr("safe_mind.core.config.settings.signal_store_provider", "sqlite")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_username", "safemind")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_password", None)


def test_eval_page_loads() -> None:
    client = TestClient(app)

    response = client.get("/eval")

    assert response.status_code == 200
    assert "SafeMind Pipeline Eval" in response.text
    assert "Alert Dashboard" in response.text
    assert "Known users in local DB" in response.text
    assert "Current test user is synthetic but stored in the real local DB" in response.text
    assert "Dataset Simulation" in response.text
    assert "CSV columns: timestamp,message" in response.text
    assert "Internal dataset simulation for historical monitoring" in response.text
    assert "Request embedding preview" not in response.text


def test_eval_router_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.enable_eval_ui", False)
    client = TestClient(create_app())

    response = client.get("/eval")

    assert response.status_code == 404


def test_eval_requires_auth_when_password_is_configured(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_username", "team")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_password", "secret")
    client = TestClient(app)

    response = client.get("/eval")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


def test_eval_accepts_configured_basic_auth(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_username", "team")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_password", "secret")
    client = TestClient(app)

    response = client.get("/eval", auth=("team", "secret"))

    assert response.status_code == 200
    assert "SafeMind Pipeline Eval" in response.text


def test_eval_fails_closed_in_production_without_password(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.env", "production")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_password", None)
    client = TestClient(app)

    response = client.get("/eval")

    assert response.status_code == 503
    assert response.json()["detail"] == "Eval auth password is not configured."


def test_eval_fails_closed_for_mongodb_without_password(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.env", "local")
    monkeypatch.setattr("safe_mind.core.config.settings.signal_store_provider", "mongodb")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_password", None)
    client = TestClient(app)

    response = client.get("/eval")

    assert response.status_code == 503
    assert response.json()["detail"] == "Eval auth password is not configured."


def test_eval_run_accepts_multiple_messages_without_vector() -> None:
    client = TestClient(app)

    response = client.post(
        "/eval/run",
        json={
            "messages": [
                "I feel overwhelmed today.",
                "Please call me at 052-123-4567",
            ],
            "persist": False,
            "create_vector": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["child_user_id"]
    assert body["runtime"]["strict_model_eval"] is True
    assert len(body["results"]) == 2
    assert body["results"][0]["logs"][0]["stage"] == "input"
    assert body["results"][0]["status"] == "no_vector"


def test_eval_dataset_run_persists_and_finalizes_timeline(monkeypatch, tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "signals.db")

    def fake_process_message(request, **kwargs):
        high_signal = "bad" in request.text.lower()
        scores = PsychologicalScores(
            positive_emotion=2 if high_signal else 7,
            negative_emotion=8 if high_signal else 2,
            loneliness=8 if high_signal else 2,
            anxiety_stress=8 if high_signal else 2,
            hopelessness=7 if high_signal else 2,
            self_worth_low=7 if high_signal else 2,
            risk=5 if high_signal else 1,
        )
        features = SignalFeatures(
            should_store=True,
            signal_strength=0.8 if high_signal else 0.2,
            risk_level="medium" if high_signal else "low",
            scores=scores,
            confidence=0.9,
            provider="heuristic",
        )
        store.initialize()
        store.save_signal_features(
            event_id=request.event_id,
            child_user_id=request.child_user_id,
            device_id=request.device_id,
            occurred_at=request.occurred_at,
            source_app=request.source_app,
            features=features,
            pipeline_version="test",
        )

    monkeypatch.setattr(eval_ui, "get_signal_store", lambda: store)
    monkeypatch.setattr(eval_ui, "process_message", fake_process_message)
    client = TestClient(app)
    dataset = "\n".join(
        ["timestamp,message"]
        + [f"2026-01-{day:02d} 12:00,normal day" for day in range(1, 11)]
        + [f"2026-01-{day:02d} 12:00,bad day" for day in range(11, 14)]
    )

    response = client.post(
        "/eval/datasets/run",
        json={
            "dataset_text": dataset,
            "dataset_format": "csv",
            "uid": "eval-team-user",
            "parent_phone": "+972500000000",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 13
    assert body["uid"] == "eval-team-user"
    assert body["start_day"] == "2026-01-01"
    assert body["end_day"] == "2026-01-13"
    assert len(body["finalized_days"]) == 13
    assert body["timeline"]["child_user_id"] == body["child_user_id"]
    assert body["timeline"]["days"][-1]["day"] == "2026-01-13"
    assert body["alerts_to_send"] >= 1
    assert any(day["alert_delivery"] == "dry_run" for day in body["finalized_days"])


def test_eval_dataset_run_reports_configured_store_failure(monkeypatch) -> None:
    class BrokenMongoStore:
        def initialize(self) -> None:
            raise RuntimeError("mongo unavailable")

    monkeypatch.setattr("safe_mind.core.config.settings.env", "local")
    monkeypatch.setattr("safe_mind.core.config.settings.signal_store_provider", "mongodb")
    monkeypatch.setattr("safe_mind.core.config.settings.eval_auth_password", "secret")
    monkeypatch.setattr(eval_ui, "get_signal_store", lambda: BrokenMongoStore())
    client = TestClient(app)

    response = client.post(
        "/eval/datasets/run",
        auth=("safemind", "secret"),
        json={
            "dataset_text": "timestamp,message\n2026-01-01 12:00,normal day",
            "dataset_format": "csv",
        },
    )

    assert response.status_code == 503
    assert "Fix the MongoDB connection and retry" in response.json()["detail"]


def test_eval_alert_timeline_returns_empty_user_timeline(monkeypatch) -> None:
    class FakeStore:
        def initialize(self) -> None:
            return None

        def list_signal_records_for_child(self, child_user_id: UUID) -> list[DailySignalRecord]:
            return []

        def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list:
            return []

    monkeypatch.setattr(eval_ui, "get_signal_store", lambda: FakeStore())
    client = TestClient(app)

    response = client.get(
        "/eval/alerts/timeline",
        params={
            "child_user_id": "fd588728-5478-44c7-b887-673581a571bc",
            "start_day": "2026-06-01",
            "days": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["child_user_id"] == "fd588728-5478-44c7-b887-673581a571bc"
    assert body["start_day"] == "2026-06-01"
    assert body["end_day"] == "2026-06-03"
    assert [day["reason"] for day in body["days"]] == ["no_signals", "no_signals", "no_signals"]


def test_eval_alert_timeline_defaults_to_last_30_days(monkeypatch) -> None:
    child_user_id = UUID("fd588728-5478-44c7-b887-673581a571bc")

    class FakeStore:
        def __init__(self, db_path: str) -> None:
            self.db_path = db_path

        def initialize(self) -> None:
            return None

        def list_signal_records_for_child(self, child_user_id: UUID) -> list[DailySignalRecord]:
            occurred_at = datetime(2026, 6, 30, 12, tzinfo=UTC)
            scores = {
                "positive_emotion": 5.0,
                "negative_emotion": 4.0,
                "loneliness": 1.0,
                "anxiety_stress": 1.0,
                "hopelessness": 1.0,
                "self_worth_low": 1.0,
                "risk": 1.0,
            }
            return [
                DailySignalRecord(
                    id=str(uuid4()),
                    child_user_id=child_user_id,
                    day=occurred_at.date(),
                    created_at=occurred_at,
                    updated_at=occurred_at,
                    message_count=1,
                    scores=scores,
                )
            ]

        def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list:
            return []

    monkeypatch.setattr(eval_ui, "get_signal_store", lambda: FakeStore("test"))
    client = TestClient(app)

    response = client.get(
        "/eval/alerts/timeline",
        params={
            "child_user_id": str(child_user_id),
            "days": 30,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["start_day"] == "2026-06-01"
    assert body["end_day"] == "2026-06-30"

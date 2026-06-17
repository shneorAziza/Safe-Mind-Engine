from fastapi.testclient import TestClient

import safe_mind.api.eval_ui as eval_ui
from safe_mind.analysis.models import SignalFeatures
from safe_mind.main import app
from safe_mind.storage.vector_store import SignalVectorRecord
from uuid import UUID, uuid4
from datetime import UTC, datetime


def test_eval_page_loads() -> None:
    client = TestClient(app)

    response = client.get("/eval")

    assert response.status_code == 200
    assert "SafeMind Pipeline Eval" in response.text
    assert "Alert Dashboard" in response.text
    assert "Known users in local DB" in response.text
    assert "Current test user is synthetic but stored in the real local DB" in response.text
    assert "load the last 30 days" in response.text
    assert "real configured models with no silent heuristic fallback" in response.text


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


def test_eval_alert_timeline_returns_empty_user_timeline() -> None:
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

        def list_signal_vectors_for_child(self, child_user_id: UUID) -> list[SignalVectorRecord]:
            return [
                SignalVectorRecord(
                    id=str(uuid4()),
                    event_id=uuid4(),
                    child_user_id=child_user_id,
                    device_id=uuid4(),
                    occurred_at=datetime(2026, 6, 30, 12, tzinfo=UTC),
                    source_app="test",
                    embedding_vector=[1.0, 0.0, 0.0],
                    features=SignalFeatures(
                        should_store=True,
                        signal_strength=0.4,
                        risk_level="low",
                        confidence=0.9,
                        provider="heuristic",
                    ),
                    pipeline_version="test",
                )
            ]

        def list_parent_alert_days_for_child(self, child_user_id: UUID) -> list:
            return []

    monkeypatch.setattr(eval_ui, "SQLiteVectorStore", FakeStore)
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

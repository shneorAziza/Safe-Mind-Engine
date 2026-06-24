from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from safe_mind.alerts.finalization_job import run_daily_finalization
from safe_mind.analysis.models import PsychologicalScores, SignalFeatures
from safe_mind.core.metrics import metrics
from safe_mind.main import app
from safe_mind.storage.vector_store import SQLiteVectorStore


def test_metrics_endpoint_returns_snapshot() -> None:
    metrics.reset()
    metrics.increment("test.counter")
    metrics.observe_ms("test.duration", 12.5)
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["counters"]["test.counter"] == 1
    assert body["timings_ms"]["test.duration"]["count"] == 1


def test_finalization_metrics_are_recorded(tmp_path) -> None:
    metrics.reset()
    store = SQLiteVectorStore(tmp_path / "signals.sqlite3")
    store.initialize()
    child_user_id = uuid4()
    device_id = uuid4()
    start = datetime(2026, 6, 1, 12, tzinfo=UTC)

    for offset in range(10):
        store.save_signal_features(
            event_id=uuid4(),
            child_user_id=child_user_id,
            device_id=device_id,
            occurred_at=start + timedelta(days=offset),
            source_app="chatgpt",
            features=_features(negative_emotion=1, loneliness=1, anxiety_stress=1),
            pipeline_version="test",
        )
    for offset in range(10, 13):
        store.save_signal_features(
            event_id=uuid4(),
            child_user_id=child_user_id,
            device_id=device_id,
            occurred_at=start + timedelta(days=offset),
            source_app="chatgpt",
            features=_features(negative_emotion=8, loneliness=8, anxiety_stress=8),
            pipeline_version="test",
        )

    run_daily_finalization(target_day=date(2026, 6, 13), store=store)
    snapshot = metrics.snapshot()

    assert snapshot["counters"]["finalization.runs.total"] == 1
    assert snapshot["counters"]["finalization.decisions.saved"] == 1
    assert snapshot["counters"]["finalization.alerts.to_send"] == 1
    assert snapshot["timings_ms"]["finalization.run.duration"]["count"] == 1


def _features(
    *,
    negative_emotion: int,
    loneliness: int,
    anxiety_stress: int,
) -> SignalFeatures:
    return SignalFeatures(
        should_store=True,
        risk_level="low",
        scores=PsychologicalScores(
            positive_emotion=5,
            negative_emotion=negative_emotion,
            loneliness=loneliness,
            anxiety_stress=anxiety_stress,
            hopelessness=1,
            self_worth_low=1,
            risk=1,
        ),
        confidence=0.9,
        provider="heuristic",
    )

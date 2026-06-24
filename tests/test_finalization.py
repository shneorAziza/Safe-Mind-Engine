from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from safe_mind.alerts.finalization import finalize_alert_day, previous_day_for_run
from safe_mind.alerts.finalization_job import run_daily_finalization
from safe_mind.analysis.models import PsychologicalScores, SignalFeatures
from safe_mind.storage.vector_store import SQLiteVectorStore


def test_previous_day_for_run_uses_closed_calendar_day() -> None:
    run_at = datetime(2026, 6, 25, 0, 5, tzinfo=UTC)

    assert previous_day_for_run(run_at) == date(2026, 6, 24)


def test_finalize_alert_day_computes_and_stores_closed_day_decision(tmp_path) -> None:
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

    pre_finalize_records = store.list_signal_records_for_child(child_user_id)
    assert pre_finalize_records[-1].should_send_alert is False

    decision = finalize_alert_day(
        child_user_id=child_user_id,
        target_day=date(2026, 6, 13),
        store=store,
    )

    assert decision is not None
    assert decision.target_day == date(2026, 6, 13)
    assert decision.should_send_push is True
    assert store.list_parent_alert_days_for_child(child_user_id) == [date(2026, 6, 13)]


def test_run_daily_finalization_returns_job_summary(tmp_path) -> None:
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

    summary = run_daily_finalization(target_day=date(2026, 6, 13), store=store)

    assert summary.target_day == date(2026, 6, 13)
    assert summary.users_checked == 1
    assert summary.decisions_saved == 1
    assert summary.alerts_to_send == 1
    assert summary.alert_child_user_ids == [str(child_user_id)]


def test_run_daily_finalization_sends_callback_for_push_decision(monkeypatch, tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "signals.sqlite3")
    store.initialize()
    child_user_id = uuid4()
    device_id = uuid4()
    start = datetime(2026, 6, 1, 12, tzinfo=UTC)
    sent = []

    def fake_send_next_alert_callback(*, decision, mapping):
        sent.append((decision, mapping))

        class Result:
            sent = True
            skipped = False

        return Result()

    monkeypatch.setattr(
        "safe_mind.alerts.finalization_job.send_next_alert_callback",
        fake_send_next_alert_callback,
    )
    store.save_next_integration_mapping(
        child_user_id=child_user_id,
        device_id=device_id,
        uid="firebase-user-id",
        external_device_id="firestore-device-id",
    )

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

    summary = run_daily_finalization(
        target_day=date(2026, 6, 13),
        send_alerts=True,
        store=store,
    )

    assert summary.alerts_to_send == 1
    assert summary.callbacks_sent == 1
    assert summary.callbacks_failed == 0
    assert summary.callbacks_skipped == 0
    assert len(sent) == 1
    assert sent[0][1].uid == "firebase-user-id"
    assert sent[0][1].external_device_id == "firestore-device-id"


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

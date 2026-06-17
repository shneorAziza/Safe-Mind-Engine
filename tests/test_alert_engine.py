from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from safe_mind.alerts.engine import compute_daily_signal_scores, evaluate_parent_alert
from safe_mind.alerts.models import AlertPolicy
from safe_mind.analysis.models import SignalFeatures
from safe_mind.storage.vector_store import SignalVectorRecord


CHILD_ID = UUID("b36ebae4-7c7f-4904-972b-04f53e9d5a55")
DEVICE_ID = UUID("bd7c7835-376b-465a-bcb5-d7a8ac52f46b")


def test_compute_daily_signal_scores_averages_message_vectors_per_day() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        _record(start, [1.0, 0.0]),
        _record(start + timedelta(hours=2), [1.0, 0.0]),
        *[_record(start + timedelta(days=offset), [1.0, 0.0]) for offset in range(1, 10)],
        _record(start + timedelta(days=10), [0.0, 1.0]),
    ]

    scores = compute_daily_signal_scores(records)

    assert len(scores) == 11
    assert scores[0].average_score == 0.0
    assert scores[0].message_count == 2
    assert scores[-1].message_count == 1
    assert scores[-1].average_score > 0.4


def test_evaluate_parent_alert_sends_push_after_three_vector_deviations_in_five_days() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), [1.0, 0.0]) for offset in range(10)],
        _record(start + timedelta(days=10), [0.0, 1.0]),
        _record(start + timedelta(days=11), [0.0, 1.0]),
        _record(start + timedelta(days=12), [0.0, 1.0]),
    ]

    decision = evaluate_parent_alert(
        child_user_id=CHILD_ID,
        records=records,
        target_day=(start + timedelta(days=12)).date(),
        policy=AlertPolicy(cooldown_days=0),
    )

    assert decision.should_send_push is True
    assert decision.reason == "gate_met"
    assert decision.deviations_in_window == 3
    assert decision.daily_score is not None
    assert decision.daily_score > 0.4


def test_evaluate_parent_alert_waits_for_enough_baseline_days() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        _record(start + timedelta(days=0), [1.0, 0.0]),
        _record(start + timedelta(days=1), [0.0, 1.0]),
    ]

    decision = evaluate_parent_alert(
        child_user_id=CHILD_ID,
        records=records,
        target_day=(start + timedelta(days=1)).date(),
    )

    assert decision.should_send_push is False
    assert decision.reason == "insufficient_baseline"


def test_evaluate_parent_alert_does_not_alert_during_first_ten_day_baseline() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), [1.0, 0.0]) for offset in range(3)],
        *[_record(start + timedelta(days=offset), [0.0, 1.0]) for offset in range(3, 6)],
    ]

    decision = evaluate_parent_alert(
        child_user_id=CHILD_ID,
        records=records,
        target_day=(start + timedelta(days=5)).date(),
    )

    assert decision.should_send_push is False
    assert decision.reason == "insufficient_baseline"


def test_evaluate_parent_alert_respects_cooldown() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), [1.0, 0.0]) for offset in range(10)],
        _record(start + timedelta(days=10), [0.0, 1.0]),
        _record(start + timedelta(days=11), [0.0, 1.0]),
        _record(start + timedelta(days=12), [0.0, 1.0]),
    ]

    decision = evaluate_parent_alert(
        child_user_id=CHILD_ID,
        records=records,
        target_day=(start + timedelta(days=12)).date(),
        previous_alert_days=[(start + timedelta(days=11)).date()],
    )

    assert decision.should_send_push is False
    assert decision.reason == "cooldown_active"


def _record(occurred_at: datetime, embedding_vector: list[float]) -> SignalVectorRecord:
    return SignalVectorRecord(
        id=str(uuid4()),
        event_id=uuid4(),
        child_user_id=CHILD_ID,
        device_id=DEVICE_ID,
        occurred_at=occurred_at,
        source_app="chatgpt",
        embedding_vector=embedding_vector,
        features=SignalFeatures(
            should_store=True,
            signal_strength=0.2,
            risk_level="low",
            confidence=0.9,
            provider="heuristic",
        ),
        pipeline_version="test",
    )

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from safe_mind.alerts.engine import (
    build_alert_timeline,
    compute_daily_signal_scores,
    rebuild_daily_alert_state,
)
from safe_mind.storage.models import DailySignalRecord


CHILD_ID = UUID("b36ebae4-7c7f-4904-972b-04f53e9d5a55")


def test_daily_records_keep_one_score_per_day() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        _record(start, negative_emotion=6, message_count=2),
        *[_record(start + timedelta(days=offset), negative_emotion=2) for offset in range(1, 10)],
        _record(start + timedelta(days=10), negative_emotion=9, loneliness=9, anxiety_stress=9),
    ]

    scores = compute_daily_signal_scores(records)

    assert len(scores) == 11
    assert scores[0].message_count == 2
    assert scores[-1].message_count == 1
    assert scores[-1].average_score > scores[0].average_score


def test_rebuild_daily_alert_state_flags_three_consecutive_deviation_days() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), negative_emotion=2) for offset in range(10)],
        _record(start + timedelta(days=10), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=11), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=12), negative_emotion=9, loneliness=9, anxiety_stress=9),
    ]

    rebuilt, baseline_scores, baseline_score = rebuild_daily_alert_state(records)

    assert baseline_scores is not None
    assert baseline_score is None
    assert rebuilt[9].is_baseline_day is True
    assert rebuilt[10].is_flagged is True
    assert rebuilt[11].is_flagged is True
    assert rebuilt[12].is_flagged is True
    assert rebuilt[12].should_send_alert is True
    assert "רגש שלילי +7 מהרגיל" in rebuilt[12].alert_reason
    assert "בדידות +8 מהרגיל" in rebuilt[12].alert_reason


def test_rebuild_daily_alert_state_requires_same_three_metrics_to_streak() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), negative_emotion=2) for offset in range(10)],
        _record(start + timedelta(days=10), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=11), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=12), negative_emotion=9, loneliness=1, anxiety_stress=9, hopelessness=9),
    ]

    rebuilt, _, _ = rebuild_daily_alert_state(records)

    assert rebuilt[10].should_send_alert is False
    assert rebuilt[11].should_send_alert is False
    assert rebuilt[12].should_send_alert is False
    assert rebuilt[12].deviations_in_window == 3


def test_rebuild_daily_alert_state_resets_metric_streaks_on_calendar_gaps() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), negative_emotion=2) for offset in range(10)],
        _record(start + timedelta(days=10), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=12), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=13), negative_emotion=9, loneliness=9, anxiety_stress=9),
    ]

    rebuilt, _, _ = rebuild_daily_alert_state(records)

    assert rebuilt[10].deviations_in_window == 1
    assert rebuilt[11].deviations_in_window == 1
    assert rebuilt[12].deviations_in_window == 2
    assert rebuilt[12].should_send_alert is False


def test_rebuild_daily_alert_state_does_not_repeat_alert_while_gate_remains_met() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        *[_record(start + timedelta(days=offset), negative_emotion=2) for offset in range(10)],
        _record(start + timedelta(days=10), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=11), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=12), negative_emotion=9, loneliness=9, anxiety_stress=9),
        _record(start + timedelta(days=13), negative_emotion=9, loneliness=9, anxiety_stress=9, hopelessness=9),
    ]

    rebuilt, _, _ = rebuild_daily_alert_state(records)

    assert rebuilt[12].should_send_alert is True
    assert rebuilt[13].should_send_alert is False


def test_rebuild_daily_alert_state_waits_for_ten_baseline_days() -> None:
    start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    records = [
        _record(start, negative_emotion=2),
        _record(start + timedelta(days=1), negative_emotion=9),
    ]

    rebuilt, baseline_scores, baseline_score = rebuild_daily_alert_state(records)

    assert baseline_scores is None
    assert baseline_score is None
    assert rebuilt[-1].should_send_alert is False
    assert rebuilt[-1].alert_reason == "insufficient_baseline"


def test_alert_timeline_counts_baseline_only_on_signal_days() -> None:
    start = datetime(2026, 1, 3, 9, tzinfo=UTC)
    records = [
        _record(start, negative_emotion=8, message_count=2),
        _record(datetime(2026, 1, 4, 8, tzinfo=UTC), negative_emotion=2),
        _record(datetime(2026, 1, 14, 21, tzinfo=UTC), negative_emotion=8),
    ]

    timeline = build_alert_timeline(
        child_user_id=CHILD_ID,
        records=records,
        start_day=datetime(2026, 1, 2, tzinfo=UTC).date(),
        end_day=datetime(2026, 1, 14, tzinfo=UTC).date(),
    )
    days = {item.day.isoformat(): item for item in timeline}

    assert days["2026-01-02"].phase == "pre_baseline"
    assert days["2026-01-03"].phase == "baseline"
    assert days["2026-01-04"].phase == "baseline"
    assert days["2026-01-05"].phase == "pre_baseline"
    assert days["2026-01-13"].phase == "pre_baseline"
    assert days["2026-01-14"].phase == "baseline"
    assert len([item for item in timeline if item.phase == "baseline"]) == 3


def _record(
    occurred_at: datetime,
    *,
    negative_emotion: int,
    loneliness: int = 1,
    anxiety_stress: int = 1,
    hopelessness: int = 1,
    message_count: int = 1,
) -> DailySignalRecord:
    scores = {
        "positive_emotion": 5.0,
        "negative_emotion": float(negative_emotion),
        "loneliness": float(loneliness),
        "anxiety_stress": float(anxiety_stress),
        "hopelessness": float(hopelessness),
        "self_worth_low": 1.0,
        "risk": 1.0,
    }
    return DailySignalRecord(
        id=str(uuid4()),
        child_user_id=CHILD_ID,
        day=occurred_at.date(),
        created_at=occurred_at,
        updated_at=occurred_at,
        message_count=message_count,
        scores=scores,
    )

from datetime import date, timedelta
from uuid import UUID

from safe_mind.alerts.models import (
    AlertPolicy,
    AlertTimelineDay,
    DailySignalScore,
    ParentAlertDecision,
    TimelinePhase,
)
from safe_mind.storage.models import DailySignalRecord

SCORE_KEYS = (
    "positive_emotion",
    "negative_emotion",
    "loneliness",
    "anxiety_stress",
    "hopelessness",
    "self_worth_low",
    "risk",
)

DISTRESS_KEYS = (
    "negative_emotion",
    "loneliness",
    "anxiety_stress",
    "hopelessness",
    "self_worth_low",
    "risk",
)

METRIC_LABELS = {
    "positive_emotion": "רגש חיובי",
    "negative_emotion": "רגש שלילי",
    "loneliness": "בדידות",
    "anxiety_stress": "חרדה/סטרס",
    "hopelessness": "חוסר תקווה",
    "self_worth_low": "ערך עצמי נמוך",
    "risk": "סיכון",
}


def score_dict_from_model(scores: object) -> dict[str, float]:
    return {key: float(getattr(scores, key)) for key in SCORE_KEYS}


def compact_distress_score(scores: dict[str, float]) -> float:
    total = sum(scores.get(key, 1.0) for key in DISTRESS_KEYS)
    total += 10 - scores.get("positive_emotion", 5.0)
    return max(min(total / 70, 1), 0)


def compute_daily_signal_scores(
    records: list[DailySignalRecord],
    policy: AlertPolicy | None = None,
) -> list[DailySignalScore]:
    del policy
    return [
        DailySignalScore(
            day=record.day,
            average_score=compact_distress_score(record.scores),
            message_count=record.message_count,
        )
        for record in sorted(records, key=lambda item: item.day)
    ]


def evaluate_parent_alert(
    *,
    child_user_id: UUID,
    records: list[DailySignalRecord],
    target_day: date | None = None,
    policy: AlertPolicy | None = None,
    previous_alert_days: list[date] | None = None,
) -> ParentAlertDecision:
    del previous_alert_days
    active_policy = policy or AlertPolicy()
    rebuilt_records, _, _ = rebuild_daily_alert_state(records, policy=active_policy)
    records_by_day = {record.day: record for record in rebuilt_records}

    if not rebuilt_records:
        return _decision(
            child_user_id=child_user_id,
            target_day=target_day or date.today(),
            policy=active_policy,
            reason="no_signals",
        )

    evaluated_day = target_day or rebuilt_records[-1].day
    today_record = records_by_day.get(evaluated_day)
    if today_record is None:
        return _decision(
            child_user_id=child_user_id,
            target_day=evaluated_day,
            policy=active_policy,
            reason="no_signals",
        )

    return _decision(
        child_user_id=child_user_id,
        target_day=evaluated_day,
        policy=active_policy,
        reason=today_record.alert_reason,
        should_send_push=today_record.should_send_alert,
        deviations_in_window=today_record.deviations_in_window,
        message_count=today_record.message_count,
    )


def build_alert_timeline(
    *,
    child_user_id: UUID,
    records: list[DailySignalRecord],
    start_day: date,
    end_day: date,
    policy: AlertPolicy | None = None,
    previous_alert_days: list[date] | None = None,
) -> list[AlertTimelineDay]:
    del previous_alert_days
    active_policy = policy or AlertPolicy()
    rebuilt_records, baseline_scores, _ = rebuild_daily_alert_state(records, policy=active_policy)
    records_by_day = {record.day: record for record in rebuilt_records}
    first_signal_day = min(records_by_day) if records_by_day else None
    baseline_records = [record for record in rebuilt_records if record.is_baseline_day]
    baseline_complete_day = (
        baseline_records[-1].day
        if len(baseline_records) >= active_policy.min_baseline_days
        else None
    )
    timeline: list[AlertTimelineDay] = []

    current_day = start_day
    while current_day <= end_day:
        record = records_by_day.get(current_day)
        timeline.append(
            AlertTimelineDay(
                day=current_day,
                phase=_phase_for_day(
                    current_day,
                    first_signal_day=first_signal_day,
                    record=record,
                    baseline_complete_day=baseline_complete_day,
                ),
                message_count=record.message_count if record else 0,
                scores=record.scores if record else None,
                baseline_scores=baseline_scores
                if record and not record.is_baseline_day and baseline_scores
                else None,
                baseline_day_count=record.baseline_day_count if record else 0,
                is_deviation=record.is_flagged if record else False,
                deviations_in_window=record.deviations_in_window if record else 0,
                should_send_push=record.should_send_alert if record else False,
                reason=record.alert_reason if record else "no_signals",
            )
        )
        current_day += timedelta(days=1)

    return timeline


def rebuild_daily_alert_state(
    records: list[DailySignalRecord],
    policy: AlertPolicy | None = None,
) -> tuple[list[DailySignalRecord], dict[str, float] | None, float | None]:
    active_policy = policy or AlertPolicy()
    ordered = sorted(records, key=lambda item: item.day)
    if not ordered:
        return [], None, None

    baseline_records = ordered[: active_policy.baseline_calibration_days]
    baseline_ready = len(baseline_records) >= active_policy.min_baseline_days
    baseline_scores = _average_score_dict(baseline_records) if baseline_ready else None
    rebuilt: list[DailySignalRecord] = []
    metric_streaks: dict[str, int] = {}

    for index, record in enumerate(ordered):
        is_baseline_day = index < active_policy.baseline_calibration_days
        if is_baseline_day or baseline_scores is None:
            deviations_in_window = 0
            should_send_alert = False
            is_flagged = False
            reason = "insufficient_baseline"
            metric_streaks = {}
        else:
            previous_record_day = rebuilt[-1].day if rebuilt else None
            if previous_record_day and record.day != previous_record_day + timedelta(days=1):
                metric_streaks = {}
            previous_ready_metric_count = len(
                [
                    streak
                    for streak in metric_streaks.values()
                    if streak >= active_policy.required_deviation_days
                ]
            )
            metric_reasons_by_key = metric_deviations(
                daily_scores=record.scores,
                baseline_scores=baseline_scores or {},
                policy=active_policy,
            )
            metric_streaks = {
                key: metric_streaks.get(key, 0) + 1
                for key in metric_reasons_by_key
            }
            alert_metric_keys = [
                key
                for key, streak in metric_streaks.items()
                if streak >= active_policy.required_deviation_days
            ]
            is_flagged = bool(metric_reasons_by_key)
            deviations_in_window = max(metric_streaks.values(), default=0)
            should_send_alert = (
                len(alert_metric_keys) >= active_policy.required_deviating_metrics
                and previous_ready_metric_count < active_policy.required_deviating_metrics
            )
            reason_keys = alert_metric_keys if should_send_alert else list(metric_reasons_by_key)
            reason = (
                "; ".join(metric_reasons_by_key[key] for key in reason_keys)
                if is_flagged
                else "below_gate"
            )

        rebuilt.append(
            record.model_copy(
                update={
                    "baseline_day_count": len(baseline_records) if baseline_ready else 0,
                    "is_baseline_day": is_baseline_day,
                    "is_flagged": is_flagged,
                    "should_send_alert": should_send_alert,
                    "alert_reason": reason,
                    "deviations_in_window": deviations_in_window,
                }
            )
        )

    return rebuilt, baseline_scores, None


def metric_deviation_reasons(
    *,
    daily_scores: dict[str, float],
    baseline_scores: dict[str, float],
    policy: AlertPolicy,
) -> list[str]:
    reasons = list(
        metric_deviations(
            daily_scores=daily_scores,
            baseline_scores=baseline_scores,
            policy=policy,
        ).values()
    )
    return reasons if len(reasons) >= policy.required_deviating_metrics else []


def metric_deviations(
    *,
    daily_scores: dict[str, float],
    baseline_scores: dict[str, float],
    policy: AlertPolicy,
) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for key in DISTRESS_KEYS:
        delta = daily_scores.get(key, 1.0) - baseline_scores.get(key, 1.0)
        threshold = (
            policy.risk_deviation_threshold
            if key == "risk"
            else policy.metric_deviation_threshold
        )
        if delta >= threshold:
            reasons[key] = _format_metric_delta(key, delta)

    positive_delta = baseline_scores.get("positive_emotion", 5.0) - daily_scores.get(
        "positive_emotion",
        5.0,
    )
    if positive_delta >= policy.positive_emotion_drop_threshold:
        reasons["positive_emotion"] = _format_metric_delta("positive_emotion", -positive_delta)

    return reasons


def _format_metric_delta(key: str, delta: float) -> str:
    label = METRIC_LABELS.get(key, key)
    sign = "+" if delta >= 0 else ""
    value = round(delta, 1)
    if float(value).is_integer():
        value_text = str(int(value))
    else:
        value_text = str(value)
    return f"{label} {sign}{value_text} מהרגיל"


def _average_score_dict(records: list[DailySignalRecord]) -> dict[str, float]:
    return {
        key: sum(record.scores.get(key, 0.0) for record in records) / len(records)
        for key in SCORE_KEYS
    }


def _phase_for_day(
    day: date,
    *,
    first_signal_day: date | None,
    record: DailySignalRecord | None,
    baseline_complete_day: date | None,
) -> TimelinePhase:
    if first_signal_day is None or day < first_signal_day:
        return "pre_baseline"
    if record and record.is_baseline_day:
        return "baseline"
    if baseline_complete_day is None or day <= baseline_complete_day:
        return "pre_baseline"
    return "monitoring"


def _decision(
    *,
    child_user_id: UUID,
    target_day: date,
    policy: AlertPolicy,
    reason: str,
    should_send_push: bool = False,
    deviations_in_window: int = 0,
    message_count: int = 0,
) -> ParentAlertDecision:
    return ParentAlertDecision(
        child_user_id=child_user_id,
        target_day=target_day,
        should_send_push=should_send_push,
        reason=reason,
        deviations_in_window=deviations_in_window,
        gate_window_days=policy.gate_window_days,
        required_deviation_days=policy.required_deviation_days,
        message_count=message_count,
    )

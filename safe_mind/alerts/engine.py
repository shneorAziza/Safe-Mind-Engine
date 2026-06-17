from collections import defaultdict
from datetime import date, timedelta
from math import sqrt
from uuid import UUID

from safe_mind.alerts.models import (
    AlertPolicy,
    AlertTimelineDay,
    DailyDeviation,
    DailySignalScore,
    ParentAlertDecision,
    TimelinePhase,
)
from safe_mind.storage.vector_store import SignalVectorRecord


def compute_daily_signal_scores(
    records: list[SignalVectorRecord],
    policy: AlertPolicy | None = None,
) -> list[DailySignalScore]:
    active_policy = policy or AlertPolicy()
    daily_centroids = _daily_centroids(records)
    baseline_centroid, _ = _baseline_centroid(
        daily_centroids,
        baseline_days=active_policy.baseline_calibration_days,
    )

    if baseline_centroid is None:
        return []

    grouped_counts: dict[date, int] = defaultdict(int)
    for record in records:
        grouped_counts[record.occurred_at.date()] += 1

    scores: list[DailySignalScore] = []
    for day, centroid in daily_centroids.items():
        scores.append(
            DailySignalScore(
                day=day,
                average_score=_cosine_distance(centroid, baseline_centroid),
                message_count=grouped_counts[day],
            )
        )
    return sorted(scores, key=lambda score: score.day)


def evaluate_parent_alert(
    *,
    child_user_id: UUID,
    records: list[SignalVectorRecord],
    target_day: date | None = None,
    policy: AlertPolicy | None = None,
    previous_alert_days: list[date] | None = None,
) -> ParentAlertDecision:
    active_policy = policy or AlertPolicy()
    daily_scores = compute_daily_signal_scores(records, policy=active_policy)
    scores_by_day = {score.day: score for score in daily_scores}

    if not daily_scores:
        return _decision(
            child_user_id=child_user_id,
            target_day=target_day or date.today(),
            policy=active_policy,
            reason="no_signals",
        )

    evaluated_day = target_day or daily_scores[-1].day
    today_score = scores_by_day.get(evaluated_day)
    if today_score is None:
        return _decision(
            child_user_id=child_user_id,
            target_day=evaluated_day,
            policy=active_policy,
            reason="no_signals",
        )

    deviations = [
        deviation
        for deviation in _deviations_for_window(
            scores_by_day=scores_by_day,
            target_day=evaluated_day,
            policy=active_policy,
        )
        if deviation.is_deviation
    ]
    target_deviation = _deviation_for_day(
        scores_by_day=scores_by_day,
        day=evaluated_day,
        policy=active_policy,
    )

    if target_deviation is None:
        return _decision(
            child_user_id=child_user_id,
            target_day=evaluated_day,
            policy=active_policy,
            reason="insufficient_baseline",
            daily_score=today_score.average_score,
            message_count=today_score.message_count,
        )

    if len(deviations) < active_policy.required_deviation_days:
        return _decision(
            child_user_id=child_user_id,
            target_day=evaluated_day,
            policy=active_policy,
            reason="below_gate",
            daily_score=today_score.average_score,
            baseline_score=target_deviation.baseline_score,
            deviations_in_window=len(deviations),
            message_count=today_score.message_count,
        )

    if _cooldown_active(evaluated_day, previous_alert_days or [], active_policy):
        return _decision(
            child_user_id=child_user_id,
            target_day=evaluated_day,
            policy=active_policy,
            reason="cooldown_active",
            daily_score=today_score.average_score,
            baseline_score=target_deviation.baseline_score,
            deviations_in_window=len(deviations),
            message_count=today_score.message_count,
        )

    return _decision(
        child_user_id=child_user_id,
        target_day=evaluated_day,
        policy=active_policy,
        reason="gate_met",
        should_send_push=True,
        daily_score=today_score.average_score,
        baseline_score=target_deviation.baseline_score,
        deviations_in_window=len(deviations),
        message_count=today_score.message_count,
    )


def build_alert_timeline(
    *,
    child_user_id: UUID,
    records: list[SignalVectorRecord],
    start_day: date,
    end_day: date,
    policy: AlertPolicy | None = None,
    previous_alert_days: list[date] | None = None,
) -> list[AlertTimelineDay]:
    active_policy = policy or AlertPolicy()
    daily_scores = compute_daily_signal_scores(records, policy=active_policy)
    scores_by_day = {score.day: score for score in daily_scores}
    first_signal_day = daily_scores[0].day if daily_scores else None
    baseline_end = (
        first_signal_day + timedelta(days=active_policy.baseline_calibration_days)
        if first_signal_day
        else None
    )
    alert_days = sorted(previous_alert_days or [])
    timeline: list[AlertTimelineDay] = []

    current_day = start_day
    while current_day <= end_day:
        score = scores_by_day.get(current_day)
        deviation = _deviation_for_day(
            scores_by_day=scores_by_day,
            day=current_day,
            policy=active_policy,
        )
        decision = evaluate_parent_alert(
            child_user_id=child_user_id,
            records=records,
            target_day=current_day,
            policy=active_policy,
            previous_alert_days=alert_days,
        )

        if decision.should_send_push:
            alert_days.append(current_day)

        timeline.append(
            AlertTimelineDay(
                day=current_day,
                phase=_phase_for_day(current_day, first_signal_day, baseline_end),
                message_count=score.message_count if score else 0,
                daily_score=score.average_score if score else None,
                baseline_score=deviation.baseline_score if deviation else None,
                baseline_day_count=deviation.baseline_day_count if deviation else 0,
                delta=deviation.delta if deviation else None,
                is_deviation=deviation.is_deviation if deviation else False,
                deviations_in_window=decision.deviations_in_window,
                should_send_push=decision.should_send_push,
                reason=decision.reason,
            )
        )
        current_day += timedelta(days=1)

    return timeline


def _deviations_for_window(
    *,
    scores_by_day: dict[date, DailySignalScore],
    target_day: date,
    policy: AlertPolicy,
) -> list[DailyDeviation]:
    window_start = target_day - timedelta(days=policy.gate_window_days - 1)
    deviations: list[DailyDeviation] = []
    for offset in range(policy.gate_window_days):
        day = window_start + timedelta(days=offset)
        deviation = _deviation_for_day(scores_by_day=scores_by_day, day=day, policy=policy)
        if deviation is not None:
            deviations.append(deviation)
    return deviations


def _deviation_for_day(
    *,
    scores_by_day: dict[date, DailySignalScore],
    day: date,
    policy: AlertPolicy,
) -> DailyDeviation | None:
    daily_score = scores_by_day.get(day)
    if daily_score is None:
        return None

    first_signal_day = min(score.day for score in scores_by_day.values())
    baseline_end = first_signal_day + timedelta(days=policy.baseline_calibration_days)
    if day < baseline_end:
        return None

    baseline_values = [
        score.average_score
        for score in scores_by_day.values()
        if first_signal_day <= score.day < baseline_end
    ]
    if len(baseline_values) < policy.min_baseline_days:
        return None

    baseline_score = sum(baseline_values) / len(baseline_values)
    delta = daily_score.average_score - baseline_score
    return DailyDeviation(
        day=day,
        daily_score=daily_score.average_score,
        baseline_score=baseline_score,
        baseline_day_count=len(baseline_values),
        delta=delta,
        is_deviation=delta >= policy.deviation_threshold,
    )


def _daily_centroids(records: list[SignalVectorRecord]) -> dict[date, list[float]]:
    grouped_vectors: dict[date, list[list[float]]] = defaultdict(list)
    for record in records:
        grouped_vectors[record.occurred_at.date()].append(record.embedding_vector)

    return {day: _mean_vector(vectors) for day, vectors in grouped_vectors.items()}


def _baseline_centroid(
    daily_centroids: dict[date, list[float]],
    baseline_days: int = 10,
) -> tuple[list[float] | None, list[date]]:
    if not daily_centroids:
        return None, []

    ordered_days = sorted(daily_centroids)
    first_signal_day = ordered_days[0]
    baseline_end = first_signal_day + timedelta(days=baseline_days)
    baseline_day_list = [day for day in ordered_days if first_signal_day <= day < baseline_end]
    if not baseline_day_list:
        return None, []

    return _mean_vector([daily_centroids[day] for day in baseline_day_list]), baseline_day_list


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dimensions = len(vectors[0])
    sums = [0.0] * dimensions
    for vector in vectors:
        for index, value in enumerate(vector):
            sums[index] += value
    return [value / len(vectors) for value in sums]


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    cosine_similarity = max(min(dot / (left_norm * right_norm), 1.0), -1.0)
    return (1 - cosine_similarity) / 2


def _cooldown_active(target_day: date, previous_alert_days: list[date], policy: AlertPolicy) -> bool:
    if policy.cooldown_days == 0:
        return False

    cooldown_start = target_day - timedelta(days=policy.cooldown_days)
    return any(cooldown_start <= alert_day < target_day for alert_day in previous_alert_days)


def _phase_for_day(
    day: date,
    first_signal_day: date | None,
    baseline_end: date | None,
) -> TimelinePhase:
    if first_signal_day is None or day < first_signal_day:
        return "pre_baseline"
    if baseline_end is not None and day < baseline_end:
        return "baseline"
    return "monitoring"


def _decision(
    *,
    child_user_id: UUID,
    target_day: date,
    policy: AlertPolicy,
    reason: str,
    should_send_push: bool = False,
    daily_score: float | None = None,
    baseline_score: float | None = None,
    deviations_in_window: int = 0,
    message_count: int = 0,
) -> ParentAlertDecision:
    return ParentAlertDecision(
        child_user_id=child_user_id,
        target_day=target_day,
        should_send_push=should_send_push,
        reason=reason,
        daily_score=daily_score,
        baseline_score=baseline_score,
        deviations_in_window=deviations_in_window,
        gate_window_days=policy.gate_window_days,
        required_deviation_days=policy.required_deviation_days,
        message_count=message_count,
    )

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from safe_mind.alerts.engine import evaluate_parent_alert
from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.storage.factory import SignalStore, get_signal_store


def previous_day_for_run(run_at: datetime | None = None) -> date:
    resolved = run_at or datetime.now(UTC)
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=UTC)
    return resolved.astimezone(UTC).date() - timedelta(days=1)


def finalize_alert_day(
    *,
    child_user_id: UUID,
    target_day: date,
    store: SignalStore | None = None,
) -> ParentAlertDecision | None:
    active_store = store or get_signal_store()
    active_store.initialize()
    records = active_store.list_signal_records_for_child(child_user_id)
    if not any(record.day == target_day for record in records):
        return None

    active_store.rebuild_daily_state(child_user_id)
    rebuilt_records = active_store.list_signal_records_for_child(child_user_id)
    decision = evaluate_parent_alert(
        child_user_id=child_user_id,
        records=rebuilt_records,
        target_day=target_day,
    )
    active_store.save_parent_alert_decision(decision)
    return decision


def finalize_previous_day(
    *,
    run_at: datetime | None = None,
    store: SignalStore | None = None,
) -> list[ParentAlertDecision]:
    active_store = store or get_signal_store()
    active_store.initialize()
    target_day = previous_day_for_run(run_at)
    decisions: list[ParentAlertDecision] = []
    for child_user_id in active_store.list_child_user_ids():
        decision = finalize_alert_day(
            child_user_id=child_user_id,
            target_day=target_day,
            store=active_store,
        )
        if decision is not None:
            decisions.append(decision)
    return decisions

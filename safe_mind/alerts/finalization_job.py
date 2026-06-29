from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from safe_mind.alerts.finalization import finalize_alert_day, previous_day_for_run
from safe_mind.core.metrics import metrics, timer
from safe_mind.integrations.parent_contacts import fetch_parent_contact
from safe_mind.integrations.whatsapp import send_parent_whatsapp_alert
from safe_mind.storage.factory import SignalStore, get_signal_store


class DailyFinalizationSummary(BaseModel):
    target_day: date
    users_checked: int = 0
    decisions_saved: int = 0
    alerts_to_send: int = 0
    whatsapp_sent: int = 0
    whatsapp_failed: int = 0
    whatsapp_skipped: int = 0
    alert_child_user_ids: list[str] = Field(default_factory=list)


def run_daily_finalization(
    *,
    target_day: date | None = None,
    run_at: datetime | None = None,
    send_alerts: bool = False,
    store: SignalStore | None = None,
) -> DailyFinalizationSummary:
    metrics.increment("finalization.runs.total")
    active_store = store or get_signal_store()
    active_store.initialize()
    resolved_day = target_day or previous_day_for_run(run_at or datetime.now(UTC))
    summary = DailyFinalizationSummary(target_day=resolved_day)

    with timer("finalization.run.duration"):
        for child_user_id in active_store.list_child_user_ids():
            summary.users_checked += 1
            decision = finalize_alert_day(
                child_user_id=child_user_id,
                target_day=resolved_day,
                store=active_store,
            )
            if decision is None:
                continue

            summary.decisions_saved += 1
            metrics.increment("finalization.decisions.saved")
            if decision.should_send_push:
                summary.alerts_to_send += 1
                metrics.increment("finalization.alerts.to_send")
                summary.alert_child_user_ids.append(str(decision.child_user_id))
                if send_alerts:
                    mapping = active_store.get_next_integration_mapping(decision.child_user_id)
                    if mapping is None:
                        summary.whatsapp_skipped += 1
                        metrics.increment("finalization.whatsapp.skipped")
                        continue
                    contact_result = fetch_parent_contact(uid=mapping.uid)
                    if not contact_result.found or contact_result.contact is None:
                        summary.whatsapp_skipped += 1
                        metrics.increment("finalization.whatsapp.skipped")
                        continue
                    result = send_parent_whatsapp_alert(
                        decision=decision,
                        contact=contact_result.contact,
                    )
                    if result.sent:
                        summary.whatsapp_sent += 1
                        metrics.increment("finalization.whatsapp.sent")
                    elif result.skipped:
                        summary.whatsapp_skipped += 1
                        metrics.increment("finalization.whatsapp.skipped")
                    else:
                        summary.whatsapp_failed += 1
                        metrics.increment("finalization.whatsapp.failed")

    return summary

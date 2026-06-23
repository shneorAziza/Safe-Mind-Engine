from safe_mind.alerts.engine import evaluate_parent_alert
from safe_mind.storage.factory import get_signal_store


def main() -> None:
    store = get_signal_store()
    store.initialize()

    total_users = 0
    total_deleted = 0
    total_saved = 0

    for child_user_id in store.list_child_user_ids():
        records = store.list_signal_records_for_child(child_user_id)
        if not records:
            continue

        total_users += 1
        total_deleted += store.delete_parent_alert_decisions_for_child(child_user_id)

        previous_alert_days = []
        for record in records:
            target_day = record.occurred_at.date()
            decision = evaluate_parent_alert(
                child_user_id=child_user_id,
                records=records,
                target_day=target_day,
                previous_alert_days=previous_alert_days,
            )
            store.save_parent_alert_decision(decision)
            total_saved += 1
            if decision.should_send_push:
                previous_alert_days.append(target_day)

        print(
            f"rebuilt child_user_id={child_user_id} "
            f"days={len(records)} "
            f"push_days={','.join(day.isoformat() for day in previous_alert_days) or 'none'}"
        )

    print(f"users={total_users}")
    print(f"deleted_decisions={total_deleted}")
    print(f"saved_decisions={total_saved}")


if __name__ == "__main__":
    main()

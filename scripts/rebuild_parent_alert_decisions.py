from safe_mind.alerts.finalization import finalize_alert_day
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
            decision = finalize_alert_day(
                child_user_id=child_user_id,
                target_day=record.day,
                store=store,
            )
            if decision is None:
                continue
            total_saved += 1
            if decision.should_send_push:
                previous_alert_days.append(record.day)

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

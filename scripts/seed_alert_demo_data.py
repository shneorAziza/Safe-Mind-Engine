from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid5

from safe_mind.alerts.engine import evaluate_parent_alert
from safe_mind.analysis.models import PsychologicalScores, SignalFeatures
from safe_mind.storage.factory import SignalStore, get_signal_store


DEMO_CHILD_USER_ID = UUID("11111111-2222-4333-8444-555555555555")
DEMO_DEVICE_ID = UUID("66666666-7777-4888-9999-aaaaaaaaaaaa")
DEMO_START_DAY = datetime(2026, 6, 1, 12, tzinfo=UTC).date()
PIPELINE_VERSION = "alert-demo-v2"

DAILY_NEGATIVE_SCORES = [
    22,
    24,
    21,
    25,
    23,
    26,
    24,
    22,
    25,
    23,
    27,
    26,
    28,
    29,
    85,
    88,
    92,
    30,
    31,
    33,
    82,
    84,
    86,
    35,
    34,
    36,
    38,
    40,
    42,
    43,
]


def main() -> None:
    store = get_signal_store()
    store.initialize()

    inserted = 0
    for index, negative_score in enumerate(DAILY_NEGATIVE_SCORES):
        day = DEMO_START_DAY + timedelta(days=index)
        occurred_at = datetime.combine(day, time(12), tzinfo=UTC)
        event_id = uuid5(DEMO_CHILD_USER_ID, f"alert-demo-{day.isoformat()}")
        if _event_exists(store, event_id):
            continue

        store.save_signal_features(
            event_id=event_id,
            child_user_id=DEMO_CHILD_USER_ID,
            device_id=DEMO_DEVICE_ID,
            occurred_at=occurred_at,
            source_app="alert-demo-seed",
            features=_features_for_score(negative_score),
            pipeline_version=PIPELINE_VERSION,
        )
        inserted += 1

    records = store.list_signal_records_for_child(DEMO_CHILD_USER_ID)
    previous_alert_days = []
    push_days = []
    for index in range(len(DAILY_NEGATIVE_SCORES)):
        target_day = DEMO_START_DAY + timedelta(days=index)
        decision = evaluate_parent_alert(
            child_user_id=DEMO_CHILD_USER_ID,
            records=records,
            target_day=target_day,
            previous_alert_days=previous_alert_days,
        )
        store.save_parent_alert_decision(decision)
        if decision.should_send_push:
            previous_alert_days.append(target_day)
            push_days.append(target_day.isoformat())

    print(f"demo_child_user_id={DEMO_CHILD_USER_ID}")
    print(f"start_day={DEMO_START_DAY.isoformat()}")
    print(f"days={len(DAILY_NEGATIVE_SCORES)}")
    print(f"inserted={inserted}")
    print(f"push_days={','.join(push_days) if push_days else 'none'}")


def _event_exists(store: SignalStore, event_id: UUID) -> bool:
    return any(record.event_id == event_id for record in store.list_signal_records_for_child(DEMO_CHILD_USER_ID))


def _features_for_score(negative_score: int) -> SignalFeatures:
    return SignalFeatures(
        should_store=True,
        risk_level="low" if negative_score < 70 else "medium",
        scores=PsychologicalScores(
            positive_emotion=max(100 - negative_score, 0),
            negative_emotion=negative_score,
            loneliness=max(negative_score - 10, 0),
            anxiety_stress=max(negative_score - 5, 0),
            hopelessness=max(negative_score - 30, 0),
            self_worth_low=max(negative_score - 35, 0),
            risk=max(negative_score - 70, 0),
        ),
        confidence=0.9,
        provider="heuristic",
    )


if __name__ == "__main__":
    main()

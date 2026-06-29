import argparse
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4, uuid5

from safe_mind import pipeline as pipeline_module
from safe_mind.alerts.finalization import finalize_alert_day
from safe_mind.core.config import settings
from safe_mind.schemas.ingestion import IngestMessageRequest
from safe_mind.storage.factory import get_signal_store


DATASET_START_DAY = date(2026, 8, 1)
DEVICE_ID = UUID("99999999-aaaa-4bbb-8ccc-dddddddddddd")
SOURCE_APP = "metric-streak-pipeline-dataset"
PIPELINE_VERSION = "metric-streak-dataset-v1"

REGULAR_MESSAGES = (
    "Can you help me organize my math homework for tonight?",
    "I want to practice English vocabulary before class tomorrow.",
    "Please help me make a short plan for my science notes.",
)

TARGET_METRIC_MESSAGES = (
    "I feel sad and alone at lunch, and I keep thinking I am worthless.",
    "After school I felt sad, alone, and worthless again while trying to focus.",
    "Tonight I feel sad and alone, like I am worthless even when I try.",
)

BREAKER_MESSAGES = (
    "I feel sad today and keep thinking I am worthless while homework piles up.",
    "I feel hopeless about catching up, and also sad and worthless.",
    "It feels hopeless tonight, with this sad worthless feeling stuck in my head.",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a deterministic 30-day per-metric streak dataset through the pipeline."
    )
    parser.add_argument("--child-user-id", type=UUID, default=None)
    parsed_args = parser.parse_args()
    child_user_id = parsed_args.child_user_id or uuid4()

    settings.psychological_analyzer_provider = "heuristic"
    settings.enable_embeddings = False
    settings.pipeline_version = PIPELINE_VERSION

    store = get_signal_store()
    store.initialize()

    inserted = 0
    for day_number in range(1, 31):
        day = DATASET_START_DAY + timedelta(days=day_number - 1)
        print(f"ingesting day {day_number}/30 {day.isoformat()}", flush=True)
        for message_index, text in enumerate(_messages_for_day(day_number), start=1):
            payload = IngestMessageRequest(
                event_id=uuid5(
                    child_user_id,
                    f"{SOURCE_APP}:{day.isoformat()}:{message_index}",
                ),
                child_user_id=child_user_id,
                device_id=DEVICE_ID,
                occurred_at=datetime.combine(
                    day,
                    time(9 + message_index, 15, tzinfo=UTC),
                ),
                source_type="notification",
                source_app=SOURCE_APP,
                text=text,
                locale="en",
            )
            result = pipeline_module.process_message(
                payload,
                debug=False,
                persist=True,
                create_vector=False,
                allow_model_fallback=False,
            )
            if not result.stored_signal.stored:
                raise RuntimeError(f"Message was not stored for day {day_number}, message {message_index}.")
            inserted += 1

    decisions = []
    for day_number in range(1, 31):
        day = DATASET_START_DAY + timedelta(days=day_number - 1)
        print(f"finalizing day {day_number}/30 {day.isoformat()}", flush=True)
        decision = finalize_alert_day(
            child_user_id=child_user_id,
            target_day=day,
            store=store,
        )
        if decision is None:
            raise RuntimeError(f"No finalization decision was created for day {day_number}.")
        decisions.append((day_number, decision))

    records = store.list_signal_records_for_child(child_user_id)
    push_days = [day_number for day_number, decision in decisions if decision.should_send_push]
    flagged_days = [index + 1 for index, record in enumerate(records) if record.is_flagged]

    print(f"metric_streak_child_user_id={child_user_id}")
    print(f"device_id={DEVICE_ID}")
    print(f"start_day={DATASET_START_DAY.isoformat()}")
    print("days=30")
    print(f"messages_inserted={inserted}")
    print(f"daily_records={len(records)}")
    print(f"flagged_day_numbers={','.join(str(day) for day in flagged_days) or 'none'}")
    print(f"push_day_numbers={','.join(str(day) for day in push_days) or 'none'}")
    print(
        "push_dates="
        + (",".join(decision.target_day.isoformat() for _, decision in decisions if decision.should_send_push) or "none")
    )


def _messages_for_day(day_number: int) -> tuple[str, str, str]:
    if day_number in {13, 14, 19, 20, 21, 23, 24, 27, 28, 29}:
        return TARGET_METRIC_MESSAGES
    if day_number in {15, 25}:
        return BREAKER_MESSAGES
    return REGULAR_MESSAGES


if __name__ == "__main__":
    main()

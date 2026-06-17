import argparse
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4, uuid5

from safe_mind import pipeline as pipeline_module  # noqa: E402
from safe_mind.core.config import settings  # noqa: E402
from safe_mind.embeddings.models import EmbeddingResult  # noqa: E402
from safe_mind.schemas.ingestion import IngestMessageRequest  # noqa: E402
from safe_mind.storage.vector_store import SQLiteVectorStore  # noqa: E402


args = argparse.ArgumentParser(
    description=(
        "Seed a synthetic 30-day message dataset through the real SafeMind pipeline. "
        "By default this uses the configured providers, including OpenAI if .env enables it."
    )
)
args.add_argument(
    "--local-offline",
    action="store_true",
    help="Use heuristic providers and a deterministic local embedding. Intended for offline dev only.",
)
args.add_argument(
    "--no-embedding",
    action="store_true",
    help=(
        "Run filter/analyzer but skip embedding/storage. This will not populate the dashboard and is "
        "only useful for quick model debugging."
    ),
)
args.add_argument(
    "--child-user-id",
    type=UUID,
    default=None,
    help="Optional child user id for this seed run. Omit to create a fresh synthetic user id.",
)

MESSAGE_PIPELINE_DEVICE_ID = UUID("77777777-8888-4999-aaaa-bbbbbbbbbbbb")
MESSAGE_PIPELINE_START_DAY = datetime(2026, 7, 1, 12, tzinfo=UTC).date()

BASELINE_MESSAGE = (
    "I had a slightly bad day at school. Can you help me calm down and organize my evening?"
)
REGULAR_MESSAGE = BASELINE_MESSAGE
HIGH_SIGNAL_MESSAGE = (
    "I feel like nobody would care if I disappeared. "
    "I feel completely alone and I do not see the point anymore."
)

# High-signal clusters are centered on day 19 and day 25. Each cluster has
# three high days inside a five-day window, so the alert gate can be inspected.
HIGH_SIGNAL_DAY_NUMBERS = {17, 18, 19, 23, 24, 25}


def main() -> None:
    parsed_args = args.parse_args()
    child_user_id = parsed_args.child_user_id or uuid4()
    if parsed_args.local_offline:
        settings.emotional_filter_provider = "heuristic"
        settings.psychological_analyzer_provider = "heuristic"
        pipeline_module.create_embedding = _create_demo_embedding

    store = SQLiteVectorStore(settings.vector_db_path)
    store.initialize()

    inserted = 0
    for day_number in range(1, 31):
        day = MESSAGE_PIPELINE_START_DAY + timedelta(days=day_number - 1)
        event_id = uuid5(child_user_id, f"message-pipeline-demo-{day.isoformat()}")
        if _event_exists(store, event_id):
            continue

        payload = IngestMessageRequest(
            event_id=event_id,
            child_user_id=child_user_id,
            device_id=MESSAGE_PIPELINE_DEVICE_ID,
            occurred_at=datetime.combine(day, time(12), tzinfo=UTC),
            source_type="manual",
            source_app="message-pipeline-demo",
            text=_message_for_day(day_number),
            locale="en",
        )
        result = pipeline_module.process_message(
            payload,
            debug=False,
            persist=True,
            create_vector=not parsed_args.no_embedding,
        )
        if result.stored_signal.stored:
            inserted += 1

    decisions = _push_decisions(store, child_user_id)
    print(f"message_pipeline_child_user_id={child_user_id}")
    print(f"start_day={MESSAGE_PIPELINE_START_DAY.isoformat()}")
    print("days=30")
    print(f"inserted={inserted}")
    print(f"push_days={','.join(decisions) if decisions else 'none'}")
    print(f"mode={'local_offline' if parsed_args.local_offline else 'configured_providers'}")


def _message_for_day(day_number: int) -> str:
    if day_number <= 10:
        return BASELINE_MESSAGE
    if day_number in HIGH_SIGNAL_DAY_NUMBERS:
        return HIGH_SIGNAL_MESSAGE
    return REGULAR_MESSAGE


def _create_demo_embedding(text: str) -> EmbeddingResult:
    checksum = sum(ord(character) for character in text) % 1000
    base = checksum / 1000
    return EmbeddingResult(
        vector=[round(base, 4), round(1 - base, 4), 0.5],
        model="demo-local-embedding",
        dimensions=3,
    )


def _event_exists(store: SQLiteVectorStore, event_id: UUID) -> bool:
    with store._connect() as connection:
        row = connection.execute(
            "select 1 from signal_vectors where event_id = ? limit 1",
            (str(event_id),),
        ).fetchone()
    return row is not None


def _push_decisions(store: SQLiteVectorStore, child_user_id: UUID) -> list[str]:
    with store._connect() as connection:
        rows = connection.execute(
            """
            select target_day
            from parent_alert_decisions
            where child_user_id = ? and should_send_push = 1
            order by target_day asc
            """,
            (str(child_user_id),),
        ).fetchall()
    return [row[0] for row in rows]


if __name__ == "__main__":
    main()

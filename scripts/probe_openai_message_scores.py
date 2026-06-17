from datetime import UTC, datetime
from uuid import UUID, uuid4

from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest


CHILD_USER_ID = UUID("99999999-aaaa-4bbb-8ccc-dddddddddddd")
DEVICE_ID = UUID("eeeeeeee-ffff-4000-8111-222222222222")

MESSAGES = [
    "I had a slightly bad day at school. Can you help me calm down and organize my evening?",
    "I feel a little stressed about homework, but I think I can handle it. Can you help me make a plan?",
    "I am upset after school and want a quiet way to relax before sleep.",
    "I feel worthless, like a failure, and nothing matters. I feel alone and I cannot stop crying tonight.",
    "I feel like nobody would care if I disappeared. I feel completely alone and I do not see the point anymore.",
    "I do not want to live anymore and I am thinking about hurting myself tonight.",
]


def main() -> None:
    for index, text in enumerate(MESSAGES, start=1):
        payload = IngestMessageRequest(
            event_id=uuid4(),
            child_user_id=CHILD_USER_ID,
            device_id=DEVICE_ID,
            occurred_at=datetime(2026, 8, index, 12, tzinfo=UTC),
            source_type="manual",
            source_app="openai-score-probe",
            text=text,
            locale="en",
        )
        result = process_message(payload, debug=False, persist=False, create_vector=False)
        features = result.signal_features
        print(f"[{index}] {text}")
        if features is None:
            print("  filtered_out")
        else:
            print(
                "  "
                f"store={features.should_store} "
                f"strength={features.signal_strength} "
                f"risk={features.risk_level} "
                f"confidence={features.confidence} "
                f"provider={features.provider}"
            )
        print(
            "  "
            f"filter_relevant={result.emotional_filter.is_emotionally_relevant} "
            f"filter_confidence={result.emotional_filter.confidence} "
            f"categories={result.emotional_filter.categories} "
            f"risk_hint={result.emotional_filter.risk_hint} "
            f"filter_provider={result.emotional_filter.provider}"
        )


if __name__ == "__main__":
    main()

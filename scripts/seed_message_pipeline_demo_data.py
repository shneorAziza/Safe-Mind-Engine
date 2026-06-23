import argparse
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4, uuid5

from safe_mind import pipeline as pipeline_module  # noqa: E402
from safe_mind.analysis.models import PsychologicalScores, SignalFeatures  # noqa: E402
from safe_mind.core.config import settings  # noqa: E402
from safe_mind.schemas.ingestion import IngestMessageRequest  # noqa: E402
from safe_mind.storage.factory import SignalStore, get_signal_store  # noqa: E402


args = argparse.ArgumentParser(
    description=(
        "Seed a synthetic 30-day message dataset through the real SafeMind pipeline. "
        "By default this uses the configured providers, including OpenAI if .env enables it."
    )
)
args.add_argument(
    "--local-offline",
    action="store_true",
    help="Use heuristic providers. Intended for offline dev only.",
)
args.add_argument(
    "--no-embedding",
    action="store_true",
    help=(
        "Deprecated compatibility flag. Embeddings are disabled by SAFE_MIND_ENABLE_EMBEDDINGS=false."
    ),
)
args.add_argument(
    "--child-user-id",
    type=UUID,
    default=None,
    help="Optional child user id for this seed run. Omit to create a fresh synthetic user id.",
)
args.add_argument(
    "--demo-scores",
    action="store_true",
    help="Seed deterministic compact analysis scores for all 30 days without storing message text.",
)

MESSAGE_PIPELINE_DEVICE_ID = UUID("77777777-8888-4999-aaaa-bbbbbbbbbbbb")
MESSAGE_PIPELINE_START_DAY = datetime(2026, 7, 1, 12, tzinfo=UTC).date()

REGULAR_MESSAGES = [
    "I feel a little stressed about math homework. Can you help me make a calm study plan?",
    "I am nervous about writing an English paragraph. Can you help me organize it?",
    "I got stuck on fractions and feel frustrated. Can you explain them simply?",
    "I have a science quiz tomorrow and feel worried. Can you make me a calm checklist?",
    "I feel awkward asking my teacher about homework. Can you help me write a polite message?",
    "I am a bit overwhelmed choosing a history project topic. Can you help me start?",
    "I feel unsure about English vocabulary. Can you help me practice without pressure?",
    "I forgot how to solve this algebra problem and feel annoyed at myself.",
    "I feel tired and stressed after school. Can you help me plan homework and rest?",
    "I am worried I will not understand photosynthesis tomorrow. Can you explain it simply?",
]

REGULAR_FOLLOWUP_MESSAGES = [
    "I feel a little embarrassed by my answer. Can you help me rewrite it clearly?",
    "I am worried I will forget formulas tomorrow. Can you help me remember them?",
    "I feel nervous about a class presentation. Can you give me three simple ideas?",
    "I feel tired after school, can you help me plan a short study session?",
    "I am anxious about the material. Can you quiz me gently?",
    "My notes feel messy and I am getting frustrated. Can you help me shorten them?",
    "I feel uneasy about tomorrow's school day. Can you help me prepare calmly?",
    "I am restless before sleep after homework. Can you suggest a calm routine?",
    "I feel behind on this topic. Can you explain it like I am new to it?",
    "I am worried about forgetting tasks this week. Can you help me make a checklist?",
    "I feel shy asking questions in class. Can you help me think of what to ask?",
    "I feel behind on homework and a bit stressed. Can you make me a simple plan?",
    "My notes are confusing and I feel stuck. Can you turn them into flashcards?",
    "I want to practice answering questions without getting too stressed.",
]

HIGH_SIGNAL_MESSAGES = [
    "I feel completely alone today, like nobody notices when I am struggling.",
    "I keep thinking I am a failure and nothing I do is good enough.",
    "I feel overwhelmed and hopeless, and I do not know how to get through tonight.",
    "Everyone seems fine without me and I feel like I am disappearing.",
    "I hate myself right now and I cannot stop thinking that things will never get better.",
    "I feel unsafe with my own thoughts tonight and I need help staying calm.",
]

# High-signal clusters are centered on day 19 and day 26. Each cluster has
# three high consecutive days, so the alert gate can be inspected.
HIGH_SIGNAL_DAY_NUMBERS = {17, 18, 19, 24, 25, 26}


def main() -> None:
    parsed_args = args.parse_args()
    child_user_id = parsed_args.child_user_id or uuid4()
    if parsed_args.local_offline:
        settings.psychological_analyzer_provider = "heuristic"
    settings.enable_embeddings = False

    store = get_signal_store()
    store.initialize()

    inserted = 0
    stored_days = []
    filtered_days = []
    for day_number in range(1, 31):
        day = MESSAGE_PIPELINE_START_DAY + timedelta(days=day_number - 1)
        event_id = uuid5(child_user_id, f"message-pipeline-demo-{day.isoformat()}")
        if _day_exists(store, child_user_id, day):
            continue

        if parsed_args.demo_scores:
            store.save_signal_features(
                event_id=event_id,
                child_user_id=child_user_id,
                device_id=MESSAGE_PIPELINE_DEVICE_ID,
                occurred_at=datetime.combine(day, time(12), tzinfo=UTC),
                source_app="message-pipeline-demo",
                features=_demo_features_for_day(day_number),
                pipeline_version=settings.pipeline_version,
            )
            inserted += 1
            stored_days.append(day_number)
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
            create_vector=False,
        )
        if result.stored_signal.stored:
            inserted += 1
            stored_days.append(day_number)
        else:
            filtered_days.append(day_number)

    _rebuild_decisions(store, child_user_id)
    decisions = _push_decisions(store, child_user_id)
    print(f"message_pipeline_child_user_id={child_user_id}")
    print(f"start_day={MESSAGE_PIPELINE_START_DAY.isoformat()}")
    print("days=30")
    print(f"inserted={inserted}")
    print(f"stored_days={','.join(str(day) for day in stored_days) or 'none'}")
    print(f"filtered_days={','.join(str(day) for day in filtered_days) or 'none'}")
    print(f"push_days={','.join(decisions) if decisions else 'none'}")
    print(f"mode={'local_offline' if parsed_args.local_offline else 'configured_providers'}")


def _message_for_day(day_number: int) -> str:
    if day_number <= 10:
        return REGULAR_MESSAGES[day_number - 1]
    if day_number in HIGH_SIGNAL_DAY_NUMBERS:
        high_index = sorted(HIGH_SIGNAL_DAY_NUMBERS).index(day_number)
        return HIGH_SIGNAL_MESSAGES[high_index]
    followup_index = (day_number - 11) % len(REGULAR_FOLLOWUP_MESSAGES)
    return REGULAR_FOLLOWUP_MESSAGES[followup_index]


def _day_exists(store: SignalStore, child_user_id: UUID, day: date) -> bool:
    return any(record.day == day for record in store.list_signal_records_for_child(child_user_id))


def _push_decisions(store: SignalStore, child_user_id: UUID) -> list[str]:
    return [day.isoformat() for day in store.list_parent_alert_days_for_child(child_user_id)]


def _rebuild_decisions(store: SignalStore, child_user_id: UUID) -> None:
    del child_user_id
    del store


def _demo_features_for_day(day_number: int) -> SignalFeatures:
    if day_number in HIGH_SIGNAL_DAY_NUMBERS:
        return SignalFeatures(
            should_store=True,
            risk_level="medium",
            scores=PsychologicalScores(
                positive_emotion=1,
                negative_emotion=9,
                loneliness=8,
                anxiety_stress=9,
                hopelessness=7,
                self_worth_low=8,
                risk=5,
            ),
            confidence=0.9,
            provider="heuristic",
        )

    return SignalFeatures(
        should_store=True,
        risk_level="none",
        scores=PsychologicalScores(
            positive_emotion=6,
            negative_emotion=2,
            loneliness=1,
            anxiety_stress=2,
            hopelessness=1,
            self_worth_low=1,
            risk=1,
        ),
        confidence=0.9,
        provider="heuristic",
    )


if __name__ == "__main__":
    main()

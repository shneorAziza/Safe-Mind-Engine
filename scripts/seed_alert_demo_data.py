from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid5

from safe_mind.alerts.engine import evaluate_parent_alert
from safe_mind.analysis.models import (
    CbtPatternScores,
    EmotionScores,
    ProtectiveSignalScores,
    SignalFeatures,
    ThemeScores,
)
from safe_mind.core.config import settings
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.storage.vector_store import SQLiteVectorStore


DEMO_CHILD_USER_ID = UUID("11111111-2222-4333-8444-555555555555")
DEMO_DEVICE_ID = UUID("66666666-7777-4888-9999-aaaaaaaaaaaa")
DEMO_START_DAY = datetime(2026, 6, 1, 12, tzinfo=UTC).date()
PIPELINE_VERSION = "alert-demo-v1"

# Thirty daily numeric scores only. Days 1-10 form the fixed baseline. Days 15,
# 16, and 17 are the first 3-of-5 deviation window, so day 17 should recommend push.
DAILY_SIGNAL_STRENGTHS = [
    0.22,
    0.24,
    0.21,
    0.25,
    0.23,
    0.26,
    0.24,
    0.22,
    0.25,
    0.23,
    0.27,
    0.26,
    0.28,
    0.29,
    0.55,
    0.58,
    0.62,
    0.30,
    0.31,
    0.33,
    0.52,
    0.54,
    0.56,
    0.35,
    0.34,
    0.36,
    0.38,
    0.40,
    0.42,
    0.43,
]


def main() -> None:
    store = SQLiteVectorStore(settings.vector_db_path)
    store.initialize()

    inserted = 0
    for index, signal_strength in enumerate(DAILY_SIGNAL_STRENGTHS):
        day = DEMO_START_DAY + timedelta(days=index)
        occurred_at = datetime.combine(day, time(12), tzinfo=UTC)
        event_id = uuid5(DEMO_CHILD_USER_ID, f"alert-demo-{day.isoformat()}")
        if _event_exists(store, event_id):
            continue

        store.save_signal_vector(
            event_id=event_id,
            child_user_id=DEMO_CHILD_USER_ID,
            device_id=DEMO_DEVICE_ID,
            occurred_at=occurred_at,
            source_app="alert-demo-seed",
            embedding=EmbeddingResult(
                vector=[round(signal_strength, 4), round(1 - signal_strength, 4), 0.25],
                model="demo-numeric-vector",
                dimensions=3,
            ),
            features=_features_for_score(signal_strength),
            pipeline_version=PIPELINE_VERSION,
        )
        inserted += 1

    records = store.list_signal_vectors_for_child(DEMO_CHILD_USER_ID)
    previous_alert_days = []
    push_days = []
    for index in range(len(DAILY_SIGNAL_STRENGTHS)):
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
    print(f"days={len(DAILY_SIGNAL_STRENGTHS)}")
    print(f"inserted={inserted}")
    print(f"push_days={','.join(push_days) if push_days else 'none'}")


def _event_exists(store: SQLiteVectorStore, event_id: UUID) -> bool:
    with store._connect() as connection:
        row = connection.execute(
            "select 1 from signal_vectors where event_id = ? limit 1",
            (str(event_id),),
        ).fetchone()
    return row is not None


def _features_for_score(signal_strength: float) -> SignalFeatures:
    return SignalFeatures(
        should_store=True,
        signal_strength=signal_strength,
        risk_level="low" if signal_strength < 0.5 else "medium",
        emotion_scores=EmotionScores(
            anxiety=min(signal_strength + 0.08, 1),
            sadness=max(signal_strength - 0.08, 0),
            loneliness=max(signal_strength - 0.12, 0),
        ),
        cbt_pattern_scores=CbtPatternScores(
            catastrophizing=max(signal_strength - 0.22, 0),
            overgeneralization=max(signal_strength - 0.18, 0),
        ),
        theme_scores=ThemeScores(
            school=min(signal_strength + 0.05, 1),
            social_rejection=max(signal_strength - 0.15, 0),
        ),
        protective_signal_scores=ProtectiveSignalScores(
            seeking_help=max(0.45 - signal_strength, 0),
            social_support=max(0.35 - signal_strength, 0),
        ),
        confidence=0.9,
        provider="heuristic",
    )


if __name__ == "__main__":
    main()

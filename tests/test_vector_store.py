import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from safe_mind.analysis.models import PsychologicalScores, SignalFeatures
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.storage.vector_store import SQLiteVectorStore


def test_sqlite_store_saves_signal_features_and_no_text_or_vector(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "signals.sqlite3")
    store.initialize()

    stored_ids = store.save_signal_features(
        event_id=uuid4(),
        child_user_id=uuid4(),
        device_id=uuid4(),
        occurred_at=datetime.now(UTC),
        source_app="chatgpt",
        features=_features(),
        pipeline_version="test",
    )

    assert stored_ids.signal_id
    assert stored_ids.daily_score_id
    assert store.count() == 1
    assert store.count_vectors() == 0
    records = store.list_signal_records_for_child(next(iter(store.list_child_user_ids())))
    assert records[0].scores["negative_emotion"] == 8

    with store._connect() as connection:
        row = connection.execute(
            "select scores_json, message_scores_json from daily_signal_scores where child_user_id = ?",
            (str(records[0].child_user_id),),
        ).fetchone()

    stored = json.dumps({"scores_json": row[0], "message_scores_json": row[1]})
    assert "summary_for_embedding" not in stored
    assert "message_text" not in stored
    assert "redacted_text" not in stored
    assert "raw_text" not in stored
    assert "vector_json" not in stored


def test_sqlite_store_averages_multiple_messages_into_one_daily_score(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "signals.sqlite3")
    store.initialize()
    child_user_id = uuid4()
    device_id = uuid4()
    occurred_at = datetime(2026, 7, 1, 9, tzinfo=UTC)

    store.save_signal_features(
        event_id=uuid4(),
        child_user_id=child_user_id,
        device_id=device_id,
        occurred_at=occurred_at,
        source_app="chatgpt",
        features=_features(negative_emotion=8),
        pipeline_version="test",
    )
    store.save_signal_features(
        event_id=uuid4(),
        child_user_id=child_user_id,
        device_id=device_id,
        occurred_at=occurred_at + timedelta(hours=2),
        source_app="chatgpt",
        features=_features(negative_emotion=4),
        pipeline_version="test",
    )

    records = store.list_signal_records_for_child(child_user_id)
    assert len(records) == 1
    assert records[0].message_count == 2
    assert records[0].scores["negative_emotion"] == 6
    assert [item.scores["negative_emotion"] for item in records[0].message_scores] == [8, 4]
    assert [item.message_text for item in records[0].message_scores] == [None, None]


def test_sqlite_store_can_attach_eval_only_message_text_to_score_history(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "signals.sqlite3")
    store.initialize()
    child_user_id = uuid4()

    store.save_signal_features(
        event_id=uuid4(),
        child_user_id=child_user_id,
        device_id=uuid4(),
        occurred_at=datetime(2026, 7, 1, 9, tzinfo=UTC),
        source_app="eval-dataset",
        features=_features(negative_emotion=7),
        pipeline_version="test",
        eval_message_text="Eval simulator message",
    )

    records = store.list_signal_records_for_child(child_user_id)
    assert records[0].message_scores[0].message_text == "Eval simulator message"


def test_sqlite_store_ignores_duplicate_event_id(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "signals.sqlite3")
    store.initialize()
    event_id = uuid4()
    child_user_id = uuid4()
    device_id = uuid4()
    occurred_at = datetime(2026, 7, 1, 9, tzinfo=UTC)

    first_ids = store.save_signal_features(
        event_id=event_id,
        child_user_id=child_user_id,
        device_id=device_id,
        occurred_at=occurred_at,
        source_app="chatgpt",
        features=_features(negative_emotion=8),
        pipeline_version="test",
    )
    duplicate_ids = store.save_signal_features(
        event_id=event_id,
        child_user_id=child_user_id,
        device_id=device_id,
        occurred_at=occurred_at,
        source_app="chatgpt",
        features=_features(negative_emotion=2),
        pipeline_version="test",
    )

    records = store.list_signal_records_for_child(child_user_id)
    assert duplicate_ids == first_ids
    assert len(records) == 1
    assert records[0].message_count == 1
    assert records[0].scores["negative_emotion"] == 8


def test_legacy_vector_store_is_still_available_for_future_reenablement(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.initialize()

    vector_id = store.save_signal_vector(
        event_id=uuid4(),
        child_user_id=uuid4(),
        device_id=uuid4(),
        occurred_at=datetime.now(UTC),
        source_app="chatgpt",
        embedding=EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            model="text-embedding-test",
            dimensions=3,
        ),
        features=_features(),
        pipeline_version="test",
    )

    assert vector_id
    assert store.count_vectors() == 1


def _features(negative_emotion: int = 8) -> SignalFeatures:
    return SignalFeatures(
        should_store=True,
        risk_level="low",
        scores=PsychologicalScores(negative_emotion=negative_emotion),
        confidence=0.9,
        provider="heuristic",
    )

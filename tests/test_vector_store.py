import json
from datetime import UTC, datetime
from uuid import uuid4

from safe_mind.analysis.models import SignalFeatures
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.storage.vector_store import SQLiteVectorStore


def test_sqlite_vector_store_saves_vector_features_and_no_text(tmp_path) -> None:
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
        features=SignalFeatures(
            should_store=True,
            signal_strength=0.8,
            risk_level="low",
            confidence=0.9,
            provider="heuristic",
        ),
        pipeline_version="test",
    )

    assert vector_id
    assert store.count() == 1
    records = store.list_signal_vectors_for_child(next(iter(store.list_child_user_ids())))
    assert records[0].embedding_vector == [0.1, 0.2, 0.3]

    with store._connect() as connection:
        row = connection.execute(
            "select vector_json, features_json from signal_vectors where id = ?",
            (vector_id,),
        ).fetchone()

    assert json.loads(row[0]) == [0.1, 0.2, 0.3]
    stored = json.dumps({"vector_json": row[0], "features_json": row[1]})
    assert "summary_for_embedding" not in stored
    assert "redacted_text" not in stored
    assert "raw_text" not in stored

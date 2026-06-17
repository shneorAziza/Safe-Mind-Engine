from datetime import UTC, datetime
from uuid import UUID

from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest


def test_debug_pipeline_can_create_vector_log_without_persisting(monkeypatch) -> None:
    def fake_create_embedding(text: str) -> EmbeddingResult:
        assert text
        return EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            model="text-embedding-test",
            dimensions=3,
        )

    monkeypatch.setattr("safe_mind.pipeline.create_embedding", fake_create_embedding)
    payload = IngestMessageRequest(
        event_id=UUID("6fbdad90-89c7-4f7a-85a3-679a0ce29952"),
        child_user_id=UUID("fd588728-5478-44c7-b887-673581a571bc"),
        device_id=UUID("1736d0fe-f1a4-410e-bca2-696d36c029c3"),
        occurred_at=datetime.now(UTC),
        source_type="manual",
        source_app="debug",
        text="I feel overwhelmed today.",
        locale="en",
    )

    result = process_message(payload, debug=True, persist=False, create_vector=True)

    assert result.stored_signal.stored is False
    assert result.stored_signal.embedding_model == "text-embedding-test"
    embedding_log = next(entry for entry in result.logs if entry.stage == "embedding_and_storage")
    assert embedding_log.output["would_store"] is False
    assert embedding_log.output["stored"] is False
    assert embedding_log.output["stored_text"] is False
    assert embedding_log.output["vector_record"]["vector_json"] == {
        "dimensions": 3,
        "preview_first_8_values": [0.1, 0.2, 0.3],
    }
    assert "features" in embedding_log.output["vector_record"]["metadata"]


def test_debug_pipeline_reports_embedding_error_without_crashing(monkeypatch) -> None:
    def fake_create_embedding(text: str) -> EmbeddingResult:
        raise RuntimeError("embedding unavailable")

    monkeypatch.setattr("safe_mind.pipeline.create_embedding", fake_create_embedding)
    payload = IngestMessageRequest(
        event_id=UUID("6fbdad90-89c7-4f7a-85a3-679a0ce29952"),
        child_user_id=UUID("fd588728-5478-44c7-b887-673581a571bc"),
        device_id=UUID("1736d0fe-f1a4-410e-bca2-696d36c029c3"),
        occurred_at=datetime.now(UTC),
        source_type="manual",
        source_app="debug",
        text="I feel overwhelmed today.",
        locale="en",
    )

    result = process_message(payload, debug=True, persist=False, create_vector=True)

    assert result.stored_signal.stored is False
    embedding_log = next(entry for entry in result.logs if entry.stage == "embedding_and_storage")
    assert embedding_log.output["stored"] is False
    assert embedding_log.output["error"]["type"] == "RuntimeError"
    assert embedding_log.output["error"]["message"] == "embedding unavailable"


def test_debug_pipeline_reports_emotional_filter_model_error_without_fallback(monkeypatch) -> None:
    def fake_run_emotional_filter(text: str, *, allow_fallback: bool = True):
        assert allow_fallback is False
        raise RuntimeError("filter unavailable")

    monkeypatch.setattr("safe_mind.pipeline.run_emotional_filter", fake_run_emotional_filter)
    payload = IngestMessageRequest(
        event_id=UUID("6fbdad90-89c7-4f7a-85a3-679a0ce29952"),
        child_user_id=UUID("fd588728-5478-44c7-b887-673581a571bc"),
        device_id=UUID("1736d0fe-f1a4-410e-bca2-696d36c029c3"),
        occurred_at=datetime.now(UTC),
        source_type="manual",
        source_app="debug",
        text="I feel overwhelmed today.",
        locale="en",
    )

    result = process_message(payload, debug=True, persist=False, create_vector=False, allow_model_fallback=False)

    assert result.stored_signal.stored is False
    assert result.emotional_filter.is_emotionally_relevant is False
    emotional_log = next(entry for entry in result.logs if entry.stage == "emotional_filter")
    assert emotional_log.output["error"]["type"] == "RuntimeError"
    assert emotional_log.output["error"]["message"] == "filter unavailable"

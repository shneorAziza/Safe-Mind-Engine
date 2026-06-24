from datetime import UTC, datetime
from uuid import UUID

import pytest

from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest


def test_debug_pipeline_does_not_create_embedding_when_vector_requested(monkeypatch, tmp_path) -> None:
    def fake_create_embedding(text: str):
        raise AssertionError("embedding service should not be called while embeddings are disabled")

    monkeypatch.setattr("safe_mind.core.config.settings.signal_db_path", str(tmp_path / "signals.sqlite3"))
    monkeypatch.setattr("safe_mind.core.config.settings.enable_embeddings", False)
    monkeypatch.setattr("safe_mind.embeddings.service.create_embedding", fake_create_embedding)
    payload = _payload()

    result = process_message(payload, debug=True, persist=False, create_vector=True)

    assert result.stored_signal.stored is False
    assert result.stored_signal.embedding_model is None
    assert not [entry for entry in result.logs if entry.stage == "embedding_and_storage"]
    storage_log = next(entry for entry in result.logs if entry.stage == "signal_storage")
    assert storage_log.output["would_store"] is False
    assert storage_log.output["stored"] is False
    assert storage_log.output["stored_text"] is False
    assert storage_log.output["storage_kind"] == "json_signal_features"


def test_pipeline_stores_signal_features_without_alert_decision(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.signal_db_path", str(tmp_path / "signals.sqlite3"))
    monkeypatch.setattr("safe_mind.core.config.settings.enable_embeddings", False)

    result = process_message(_payload(), debug=True, persist=True, create_vector=True)

    assert result.stored_signal.stored is True
    assert result.stored_signal.signal_id
    assert result.stored_signal.vector_id is None
    assert result.stored_signal.embedding_model is None
    assert result.alert_decision is None


def test_debug_pipeline_reports_analyzer_model_error_without_fallback(monkeypatch) -> None:
    def fake_run_psychological_analyzer(text: str, *, allow_fallback: bool = True):
        assert allow_fallback is False
        raise RuntimeError("analyzer unavailable")

    monkeypatch.setattr("safe_mind.pipeline.run_psychological_analyzer", fake_run_psychological_analyzer)

    result = process_message(_payload(), debug=True, persist=False, create_vector=False, allow_model_fallback=False)

    assert result.stored_signal.stored is False
    analyzer_log = next(entry for entry in result.logs if entry.stage == "psychological_analyzer")
    assert analyzer_log.output["error"]["type"] == "RuntimeError"
    assert analyzer_log.output["error"]["message"] == "analyzer unavailable"


@pytest.fixture(autouse=True)
def _force_heuristics(monkeypatch) -> None:
    monkeypatch.setattr("safe_mind.core.config.settings.psychological_analyzer_provider", "heuristic")


def _payload() -> IngestMessageRequest:
    return IngestMessageRequest(
        event_id=UUID("6fbdad90-89c7-4f7a-85a3-679a0ce29952"),
        child_user_id=UUID("fd588728-5478-44c7-b887-673581a571bc"),
        device_id=UUID("1736d0fe-f1a4-410e-bca2-696d36c029c3"),
        occurred_at=datetime.now(UTC),
        source_type="manual",
        source_app="debug",
        text="I feel overwhelmed today.",
        locale="en",
    )

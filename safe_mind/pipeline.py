from typing import Any

from pydantic import BaseModel, Field

from safe_mind.alerts.engine import evaluate_parent_alert
from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.analysis.service import run_psychological_analyzer
from safe_mind.core.config import settings
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.privacy.models import PrivacySummary
from safe_mind.privacy.redactor import redact_text
from safe_mind.schemas.ingestion import IngestMessageRequest
from safe_mind.storage.factory import SignalStore, get_signal_store
from safe_mind.storage.models import StoredSignal
from safe_mind.storage.vector_store import SQLiteVectorStore


class PipelineLogEntry(BaseModel):
    stage: str
    input: Any = None
    output: Any = None


class MessagePipelineResult(BaseModel):
    privacy: PrivacySummary
    signal_features: SignalFeatures | None = None
    stored_signal: StoredSignal = Field(default_factory=lambda: StoredSignal(stored=False))
    alert_decision: ParentAlertDecision | None = None
    logs: list[PipelineLogEntry] = Field(default_factory=list)


def _error_payload(exc: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
    }
    cause = exc.__cause__
    if cause is not None:
        payload["cause_type"] = type(cause).__name__
        payload["cause_message"] = str(cause)
        nested_cause = cause.__cause__
        if nested_cause is not None:
            payload["root_cause_type"] = type(nested_cause).__name__
            payload["root_cause_message"] = str(nested_cause)
    return payload


def _configured_analyzer_model() -> str | None:
    if settings.psychological_analyzer_provider == "openai":
        return settings.openai_psychological_analyzer_model
    if settings.psychological_analyzer_provider == "bedrock":
        return settings.bedrock_psychological_analyzer_model
    return None


def process_message(
    payload: IngestMessageRequest,
    *,
    debug: bool = False,
    persist: bool = True,
    create_vector: bool | None = None,
    allow_model_fallback: bool = True,
    signal_store: SignalStore | None = None,
    eval_message_text: str | None = None,
) -> MessagePipelineResult:
    logs: list[PipelineLogEntry] = []
    requested_vector = persist if create_vector is None else create_vector
    should_create_vector = settings.enable_embeddings and requested_vector

    if debug:
        logs.append(
            PipelineLogEntry(
                stage="input",
                input={"text": payload.text},
                output={"event_id": str(payload.event_id), "source_app": payload.source_app},
            )
        )

    redaction = redact_text(payload.text)
    privacy = PrivacySummary(
        pii_detected=redaction.pii_detected,
        pii_types=redaction.pii_types,
        redaction_count=redaction.redaction_count,
        risk_level=redaction.risk_level,
    )
    if debug:
        logs.append(
            PipelineLogEntry(
                stage="privacy_redaction",
                input={"text": payload.text},
                output={
                    "redacted_text": redaction.redacted_text,
                    "privacy": privacy.model_dump(),
                },
            )
        )

    try:
        psychological_analysis = run_psychological_analyzer(
            redaction.redacted_text,
            allow_fallback=allow_model_fallback,
        )
    except Exception as exc:
        if debug:
            logs.append(
                PipelineLogEntry(
                    stage="psychological_analyzer",
                    input={"redacted_text": redaction.redacted_text},
                    output={
                        "error": _error_payload(exc),
                        "configured_provider": settings.psychological_analyzer_provider,
                        "configured_model": _configured_analyzer_model(),
                    },
                )
            )
        return MessagePipelineResult(
            privacy=privacy,
            logs=logs,
        )
    if psychological_analysis is None:
        return MessagePipelineResult(
            privacy=privacy,
            logs=logs,
        )

    if debug:
        logs.append(
            PipelineLogEntry(
                stage="psychological_analyzer",
                input={"redacted_text": redaction.redacted_text},
                output={
                    "signal_features": psychological_analysis.features.model_dump(),
                    "configured_provider": settings.psychological_analyzer_provider,
                    "configured_model": _configured_analyzer_model(),
                },
            )
        )

    stored_signal = StoredSignal(stored=False)
    alert_decision: ParentAlertDecision | None = None
    if psychological_analysis.features.should_store:
        if persist:
            stored_signal = _store_signal_features(
                payload,
                psychological_analysis.features,
                store=signal_store,
                eval_message_text=eval_message_text,
            )
        if debug:
            logs.append(
                PipelineLogEntry(
                    stage="signal_storage",
                    output={
                        "would_store": persist,
                        "stored": stored_signal.stored,
                        "stored_text": False,
                        "storage_kind": "json_signal_features",
                        "signal_features": psychological_analysis.features.model_dump(),
                        "alert_decision": alert_decision.model_dump() if alert_decision else None,
                        "signal_record": {
                            "signal_id": stored_signal.signal_id,
                        },
                    },
                )
            )

    if psychological_analysis.features.should_store and should_create_vector:
        try:
            if not psychological_analysis.summary_for_embedding:
                raise RuntimeError("summary_for_embedding is required when embeddings are enabled.")
            from safe_mind.embeddings.service import create_embedding

            embedding = create_embedding(psychological_analysis.summary_for_embedding)
            vector_metadata = _vector_metadata(payload, embedding, psychological_analysis.features)
            if persist:
                stored_signal, alert_decision = _store_embedding_and_evaluate_alert(
                    payload,
                    embedding,
                    psychological_analysis.features,
                )
            else:
                stored_signal = StoredSignal(
                    stored=False,
                    embedding_model=embedding.model,
                    embedding_dimensions=embedding.dimensions,
                )
            if debug:
                logs.append(
                    PipelineLogEntry(
                        stage="embedding_and_storage",
                        input={"summary_for_embedding": psychological_analysis.summary_for_embedding},
                        output={
                            "would_store": persist,
                            "stored": stored_signal.stored,
                            "stored_text": False,
                            "configured_provider": "openai" if settings.openai_api_key else None,
                            "configured_model": settings.openai_embedding_model,
                            "alert_decision": alert_decision.model_dump() if alert_decision else None,
                            "vector_record": {
                                "vector_json": {
                                    "dimensions": embedding.dimensions,
                                    "preview_first_8_values": embedding.vector[:8],
                                },
                                "metadata": vector_metadata,
                            },
                            "vector_id": stored_signal.vector_id,
                        },
                    )
                )
        except Exception as exc:
            if debug:
                logs.append(
                    PipelineLogEntry(
                        stage="embedding_and_storage",
                        input={"summary_for_embedding": psychological_analysis.summary_for_embedding},
                        output={
                            "would_store": persist,
                            "stored": False,
                            "stored_text": False,
                            "configured_provider": "openai" if settings.openai_api_key else None,
                            "configured_model": settings.openai_embedding_model,
                            "error": _error_payload(exc),
                        },
                    )
                )

    return MessagePipelineResult(
        privacy=privacy,
        signal_features=psychological_analysis.features,
        stored_signal=stored_signal,
        alert_decision=alert_decision,
        logs=logs,
    )


def _vector_metadata(
    payload: IngestMessageRequest,
    embedding: EmbeddingResult,
    features: SignalFeatures,
) -> dict[str, Any]:
    return {
        "event_id": str(payload.event_id),
        "child_user_id": str(payload.child_user_id),
        "device_id": str(payload.device_id),
        "occurred_at": payload.occurred_at.isoformat(),
        "source_app": payload.source_app,
        "embedding_model": embedding.model,
        "embedding_dimensions": embedding.dimensions,
        "features": features.model_dump(),
        "pipeline_version": settings.pipeline_version,
    }


def _store_embedding_and_evaluate_alert(
    payload: IngestMessageRequest,
    embedding: EmbeddingResult,
    features: SignalFeatures,
) -> tuple[StoredSignal, ParentAlertDecision]:
    store = SQLiteVectorStore(settings.vector_db_path)
    store.initialize()
    vector_id = store.save_signal_vector(
        event_id=payload.event_id,
        child_user_id=payload.child_user_id,
        device_id=payload.device_id,
        occurred_at=payload.occurred_at,
        source_app=payload.source_app,
        embedding=embedding,
        features=features,
        pipeline_version=settings.pipeline_version,
    )
    alert_decision = evaluate_parent_alert(
        child_user_id=payload.child_user_id,
        records=store.list_signal_vectors_for_child(payload.child_user_id),
        target_day=payload.occurred_at.date(),
        previous_alert_days=store.list_parent_alert_days_for_child(payload.child_user_id),
    )
    store.save_parent_alert_decision(alert_decision)
    return StoredSignal(
        stored=True,
        vector_id=vector_id,
        embedding_model=embedding.model,
        embedding_dimensions=embedding.dimensions,
    ), alert_decision


def _store_signal_features(
    payload: IngestMessageRequest,
    features: SignalFeatures,
    *,
    store: SignalStore | None = None,
    eval_message_text: str | None = None,
) -> StoredSignal:
    active_store = store or get_signal_store()
    active_store.initialize()
    stored_ids = active_store.save_signal_features(
        event_id=payload.event_id,
        child_user_id=payload.child_user_id,
        device_id=payload.device_id,
        occurred_at=payload.occurred_at,
        source_app=payload.source_app,
        features=features,
        pipeline_version=settings.pipeline_version,
        eval_message_text=eval_message_text,
    )
    return StoredSignal(
        stored=True,
        signal_id=stored_ids.signal_id,
        daily_score_id=stored_ids.daily_score_id,
    )

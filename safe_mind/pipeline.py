from typing import Any

from pydantic import BaseModel, Field

from safe_mind.alerts.engine import evaluate_parent_alert
from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.analysis.models import SignalFeatures
from safe_mind.analysis.service import run_psychological_analyzer
from safe_mind.core.config import settings
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.embeddings.service import create_embedding
from safe_mind.privacy.models import PrivacySummary
from safe_mind.privacy.redactor import redact_text
from safe_mind.schemas.ingestion import IngestMessageRequest
from safe_mind.signals.emotional_filter import EmotionalFilterResult
from safe_mind.signals.service import run_emotional_filter
from safe_mind.storage.models import StoredSignal
from safe_mind.storage.vector_store import SQLiteVectorStore


class PipelineLogEntry(BaseModel):
    stage: str
    input: Any = None
    output: Any = None


class MessagePipelineResult(BaseModel):
    privacy: PrivacySummary
    emotional_filter: EmotionalFilterResult
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


def process_message(
    payload: IngestMessageRequest,
    *,
    debug: bool = False,
    persist: bool = True,
    create_vector: bool | None = None,
    allow_model_fallback: bool = True,
) -> MessagePipelineResult:
    logs: list[PipelineLogEntry] = []
    should_create_vector = persist if create_vector is None else create_vector

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
        emotional_filter = run_emotional_filter(
            redaction.redacted_text,
            allow_fallback=allow_model_fallback,
        )
    except Exception as exc:
        if debug:
            logs.append(
                PipelineLogEntry(
                    stage="emotional_filter",
                    input={"redacted_text": redaction.redacted_text},
                    output={
                        "error": _error_payload(exc),
                        "configured_provider": settings.emotional_filter_provider,
                        "configured_model": settings.openai_emotional_filter_model
                        if settings.emotional_filter_provider == "openai"
                        else None,
                    },
                )
            )
        return MessagePipelineResult(
            privacy=privacy,
            emotional_filter=EmotionalFilterResult(
                is_emotionally_relevant=False,
                confidence=0,
                categories=[],
                risk_hint="none",
                provider=settings.emotional_filter_provider,
            ),
            logs=logs,
        )
    if debug:
        logs.append(
            PipelineLogEntry(
                stage="emotional_filter",
                input={"redacted_text": redaction.redacted_text},
                output={
                    **emotional_filter.model_dump(),
                    "configured_provider": settings.emotional_filter_provider,
                    "configured_model": settings.openai_emotional_filter_model
                    if settings.emotional_filter_provider == "openai"
                    else None,
                },
            )
        )

    try:
        psychological_analysis = run_psychological_analyzer(
            redaction.redacted_text,
            emotional_filter,
            allow_fallback=allow_model_fallback,
        )
    except Exception as exc:
        if debug:
            logs.append(
                PipelineLogEntry(
                    stage="psychological_analyzer",
                    input={
                        "redacted_text": redaction.redacted_text,
                        "emotional_filter": emotional_filter.model_dump(),
                    },
                    output={
                        "error": _error_payload(exc),
                        "configured_provider": settings.psychological_analyzer_provider,
                        "configured_model": settings.openai_psychological_analyzer_model
                        if settings.psychological_analyzer_provider == "openai"
                        else None,
                    },
                )
            )
        return MessagePipelineResult(
            privacy=privacy,
            emotional_filter=emotional_filter,
            logs=logs,
        )
    if psychological_analysis is None:
        return MessagePipelineResult(
            privacy=privacy,
            emotional_filter=emotional_filter,
            logs=logs,
        )

    if debug:
        logs.append(
            PipelineLogEntry(
                stage="psychological_analyzer",
                input={
                    "redacted_text": redaction.redacted_text,
                    "emotional_filter": emotional_filter.model_dump(),
                },
                output={
                    "signal_features": psychological_analysis.features.model_dump(),
                    "summary_for_embedding": psychological_analysis.summary_for_embedding,
                    "configured_provider": settings.psychological_analyzer_provider,
                    "configured_model": settings.openai_psychological_analyzer_model
                    if settings.psychological_analyzer_provider == "openai"
                    else None,
                },
            )
        )

    stored_signal = StoredSignal(stored=False)
    alert_decision: ParentAlertDecision | None = None
    if psychological_analysis.features.should_store and should_create_vector:
        try:
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
        emotional_filter=emotional_filter,
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

from fastapi import APIRouter, status

from safe_mind.core.config import settings
from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest, IngestMessageResponse

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])


@router.post("/messages", response_model=IngestMessageResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_message(payload: IngestMessageRequest) -> IngestMessageResponse:
    result = process_message(payload, debug=False, persist=settings.persist_signals)

    return IngestMessageResponse(
        event_id=payload.event_id,
        status="accepted",
        pipeline_stage="psychologically_analyzed",
        privacy=result.privacy,
        signal_features=result.signal_features,
        stored_signal=result.stored_signal,
        alert_decision=result.alert_decision,
    )

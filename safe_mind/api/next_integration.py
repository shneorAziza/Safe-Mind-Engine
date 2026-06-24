import secrets
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from safe_mind.core.config import settings
from safe_mind.core.metrics import metrics, timer
from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest
from safe_mind.storage.factory import get_signal_store

router = APIRouter(prefix="/v1/integrations/next", tags=["next-integration"])


class NextMessage(BaseModel):
    message_id: str | None = Field(default=None, alias="messageId", max_length=200)
    text: str = Field(min_length=1, max_length=10000)
    timestamp: int = Field(ge=0)
    source_app: str | None = Field(default=None, alias="sourceApp", max_length=120)
    locale: str | None = Field(default=None, max_length=16)

    model_config = ConfigDict(populate_by_name=True)


class NextBatchIngestRequest(BaseModel):
    uid: str = Field(min_length=1, max_length=200)
    device_id: str = Field(alias="deviceId", min_length=1, max_length=200)
    messages: list[NextMessage] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(populate_by_name=True)


class NextAcceptedEvent(BaseModel):
    message_id: str | None = Field(default=None, alias="messageId")
    event_id: UUID = Field(alias="eventId")
    status: str

    model_config = ConfigDict(populate_by_name=True)


class NextBatchIngestResponse(BaseModel):
    received: int
    accepted: int
    child_user_id: UUID = Field(alias="childUserId")
    device_id: UUID = Field(alias="deviceId")
    events: list[NextAcceptedEvent]

    model_config = ConfigDict(populate_by_name=True)


@router.post("/messages", response_model=NextBatchIngestResponse)
def ingest_next_messages(
    payload: NextBatchIngestRequest,
    authorization: str | None = Header(default=None),
) -> NextBatchIngestResponse:
    metrics.increment("next_ingest.requests.total")
    metrics.increment("next_ingest.messages.received", len(payload.messages))
    _require_integration_auth(authorization)

    child_user_id = _stable_uuid("firebase-user", payload.uid)
    device_id = _stable_uuid("firebase-device", payload.uid, payload.device_id)
    store = get_signal_store()
    store.initialize()
    store.save_next_integration_mapping(
        child_user_id=child_user_id,
        device_id=device_id,
        uid=payload.uid,
        external_device_id=payload.device_id,
    )
    events: list[NextAcceptedEvent] = []

    with timer("next_ingest.batch.duration"):
        for message in payload.messages:
            event_id = _message_event_id(
                uid=payload.uid,
                device_id=payload.device_id,
                message=message,
            )
            request = IngestMessageRequest(
                event_id=event_id,
                child_user_id=child_user_id,
                device_id=device_id,
                occurred_at=datetime.fromtimestamp(message.timestamp / 1000, tz=UTC),
                source_type="notification",
                source_app=message.source_app,
                text=message.text,
                locale=message.locale,
            )
            with timer("next_ingest.message.duration"):
                process_message(request, debug=False, persist=settings.persist_signals)
            metrics.increment("next_ingest.messages.accepted")
            events.append(
                NextAcceptedEvent(
                    message_id=message.message_id,
                    event_id=event_id,
                    status="accepted",
                )
            )

    return NextBatchIngestResponse(
        received=len(payload.messages),
        accepted=len(events),
        child_user_id=child_user_id,
        device_id=device_id,
        events=events,
    )


def _require_integration_auth(authorization: str | None) -> None:
    token = settings.integration_api_token
    if not token:
        if settings.env.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Integration API token is not configured.",
            )
        return

    expected = f"Bearer {token}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Integration authentication required.",
        )


def _stable_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "safe-mind:" + ":".join(parts))


def _message_event_id(*, uid: str, device_id: str, message: NextMessage) -> UUID:
    stable_message_key = message.message_id or f"{message.timestamp}:{message.text}"
    return _stable_uuid("message", uid, device_id, stable_message_key)

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from safe_mind.core.config import settings
from safe_mind.integrations.sms_verification import send_verification_code
from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import (
    AppAcceptedMessage,
    AppMessagesResponse,
    IngestMessageRequest,
    StoredSignalAck,
)
from safe_mind.storage.factory import SignalStore, get_signal_store
from safe_mind.storage.models import AppUser

router = APIRouter(prefix="/v1", tags=["app-auth"])


class StartAuthRequest(BaseModel):
    device_id: str = Field(alias="deviceId", min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(alias="phoneNumber", min_length=5, max_length=40)

    model_config = ConfigDict(populate_by_name=True)


class StartAuthResponse(BaseModel):
    challenge_id: str = Field(alias="challengeId")
    status: Literal["verification_sent"]
    expires_at: datetime = Field(alias="expiresAt")

    model_config = ConfigDict(populate_by_name=True)


class VerifyAuthRequest(BaseModel):
    challenge_id: str = Field(alias="challengeId", min_length=1, max_length=80)
    phone_number: str = Field(alias="phoneNumber", min_length=5, max_length=40)
    code: str = Field(min_length=4, max_length=12)

    model_config = ConfigDict(populate_by_name=True)


class AuthUserResponse(BaseModel):
    child_user_id: UUID = Field(alias="childUserId")
    device_id: UUID = Field(alias="deviceId")
    external_device_id: str = Field(alias="externalDeviceId")
    name: str
    phone_number: str = Field(alias="phoneNumber")

    model_config = ConfigDict(populate_by_name=True)


class VerifyAuthResponse(AuthUserResponse):
    token: str


class UpdateNameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AppMessageItem(BaseModel):
    message_id: str | None = Field(default=None, alias="messageId", max_length=200)
    event_id: UUID | None = Field(default=None, alias="eventId")
    occurred_at: datetime | None = Field(default=None, alias="occurredAt")
    timestamp: int | None = Field(default=None, ge=0)
    source_type: Literal["notification", "share_intent", "accessibility", "manual"] = Field(
        default="notification",
        alias="sourceType",
    )
    source_app: str | None = Field(default=None, alias="sourceApp", max_length=120)
    text: str = Field(min_length=1, max_length=10000)
    locale: str | None = Field(default=None, max_length=16)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def require_message_time(self) -> "AppMessageItem":
        if self.occurred_at is None and self.timestamp is None:
            raise ValueError("Provide occurredAt or timestamp.")
        return self

    def resolved_occurred_at(self) -> datetime:
        if self.occurred_at is not None:
            return self.occurred_at
        if self.timestamp is None:
            raise ValueError("Provide occurredAt or timestamp.")
        return datetime.fromtimestamp(self.timestamp / 1000, tz=UTC)


class AppMessagesRequest(BaseModel):
    device_id: str = Field(alias="deviceId", min_length=1, max_length=200)
    messages: list[AppMessageItem] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(populate_by_name=True)


def require_app_user(authorization: str | None = Header(default=None)) -> AppUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="App authentication required.",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="App authentication required.",
        )
    user = get_signal_store().get_app_user_by_token_hash(_hash_secret(token))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid app token.",
        )
    return user


@router.post("/auth/start", response_model=StartAuthResponse)
def start_auth(payload: StartAuthRequest) -> StartAuthResponse:
    store = get_signal_store()
    store.initialize()
    code = _verification_code()
    challenge_id = str(uuid4())
    phone_number = _normalize_phone(payload.phone_number)
    child_user_id = _stable_uuid("app-user", phone_number, payload.device_id)
    device_id = _stable_uuid("app-device", phone_number, payload.device_id)
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    send_result = send_verification_code(phone_number=phone_number, code=code)
    if not send_result.sent:
        detail = "Verification code delivery failed."
        if send_result.error:
            detail = f"{detail} {send_result.error}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    store.create_login_challenge(
        challenge_id=challenge_id,
        child_user_id=child_user_id,
        device_id=device_id,
        external_device_id=payload.device_id,
        name=payload.name.strip(),
        parent_phone=phone_number,
        code_hash=_hash_secret(code),
        expires_at=expires_at,
    )

    return StartAuthResponse(
        challenge_id=challenge_id,
        status="verification_sent",
        expires_at=expires_at,
    )


@router.post("/auth/verify", response_model=VerifyAuthResponse)
def verify_auth(payload: VerifyAuthRequest) -> VerifyAuthResponse:
    store = get_signal_store()
    store.initialize()
    pending_user = store.consume_login_challenge(
        challenge_id=payload.challenge_id,
        parent_phone=_normalize_phone(payload.phone_number),
        code_hash=_hash_secret(payload.code),
        now=datetime.now(UTC),
    )
    if pending_user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    token = secrets.token_urlsafe(48)
    user = store.upsert_app_user(
        child_user_id=pending_user.child_user_id,
        device_id=pending_user.device_id,
        external_device_id=pending_user.external_device_id,
        name=pending_user.name,
        parent_phone=pending_user.parent_phone,
        token_hash=_hash_secret(token),
    )
    return _auth_response(user, token=token)


@router.get("/me", response_model=AuthUserResponse)
def get_me(user: AppUser = Depends(require_app_user)) -> AuthUserResponse:
    return _user_response(user)


@router.patch("/me", response_model=AuthUserResponse)
def update_me(
    payload: UpdateNameRequest,
    user: AppUser = Depends(require_app_user),
) -> AuthUserResponse:
    store = get_signal_store()
    updated = store.update_app_user_name(child_user_id=user.child_user_id, name=payload.name.strip())
    return _user_response(updated)


@router.post(
    "/app/messages",
    response_model=AppMessagesResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_app_messages(
    payload: AppMessagesRequest,
    user: AppUser = Depends(require_app_user),
) -> AppMessagesResponse:
    if payload.device_id != user.external_device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device id does not match the authenticated user.",
        )

    events: list[AppAcceptedMessage] = []
    for message in payload.messages:
        event_id = message.event_id or _app_message_event_id(user=user, message=message)
        occurred_at = message.resolved_occurred_at()
        request = IngestMessageRequest(
            event_id=event_id,
            child_user_id=user.child_user_id,
            device_id=user.device_id,
            occurred_at=occurred_at,
            source_type=message.source_type,
            source_app=message.source_app,
            text=message.text,
            locale=message.locale,
        )
        result = process_message(request, debug=False, persist=settings.persist_signals)
        events.append(
            AppAcceptedMessage(
                message_id=message.message_id,
                event_id=event_id,
                status="accepted",
                stored_signal=StoredSignalAck(
                    stored=result.stored_signal.stored,
                    signal_id=result.stored_signal.signal_id,
                    daily_score_id=result.stored_signal.daily_score_id,
                ),
            )
        )

    return AppMessagesResponse(
        received=len(payload.messages),
        accepted=len(events),
        events=events,
    )


def _auth_response(user: AppUser, *, token: str) -> VerifyAuthResponse:
    return VerifyAuthResponse(**_user_response(user).model_dump(), token=token)


def _user_response(user: AppUser) -> AuthUserResponse:
    return AuthUserResponse(
        child_user_id=user.child_user_id,
        device_id=user.device_id,
        external_device_id=user.external_device_id,
        name=user.name,
        phone_number=user.parent_phone,
    )


def _verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_phone(phone_number: str) -> str:
    return phone_number.strip().replace(" ", "").replace("-", "")


def _stable_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "safe-mind:" + ":".join(parts))


def _app_message_event_id(*, user: AppUser, message: AppMessageItem) -> UUID:
    occurred_at = message.resolved_occurred_at()
    stable_message_key = message.message_id or f"{occurred_at.isoformat()}:{message.text}"
    return _stable_uuid(
        "app-message",
        str(user.child_user_id),
        user.external_device_id,
        stable_message_key,
    )

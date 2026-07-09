import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from safe_mind.core.config import settings
from safe_mind.core.metrics import metrics, timer


class VerificationCodeSendResult(BaseModel):
    sent: bool
    skipped: bool = False
    error: str | None = None


def send_verification_code(
    *,
    phone_number: str,
    code: str,
    access_token: str | None = None,
    phone_number_id: str | None = None,
    template_name: str | None = None,
    template_language: str | None = None,
    graph_api_version: str | None = None,
) -> VerificationCodeSendResult:
    resolved_token = access_token if access_token is not None else settings.whatsapp_access_token
    resolved_phone_number_id = (
        phone_number_id if phone_number_id is not None else settings.whatsapp_phone_number_id
    )
    resolved_template_name = (
        template_name
        if template_name is not None
        else settings.whatsapp_verification_template_name
    )
    resolved_language = (
        template_language
        if template_language is not None
        else settings.whatsapp_verification_template_language
    )
    resolved_version = graph_api_version if graph_api_version is not None else settings.whatsapp_graph_api_version

    missing = [
        name
        for name, value in (
            ("whatsapp_access_token", resolved_token),
            ("whatsapp_phone_number_id", resolved_phone_number_id),
            ("whatsapp_verification_template_name", resolved_template_name),
        )
        if not value
    ]
    if missing:
        metrics.increment("verification_code.skipped")
        return VerificationCodeSendResult(sent=False, skipped=True, error="missing_config:" + ",".join(missing))

    payload = _verification_template_payload(
        to=phone_number,
        code=code,
        template_name=str(resolved_template_name),
        template_language=str(resolved_language),
    )
    request = Request(
        f"https://graph.facebook.com/{resolved_version}/{resolved_phone_number_id}/messages",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resolved_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    metrics.increment("verification_code.requests.total")
    try:
        with timer("verification_code.duration"):
            with urlopen(request, timeout=15) as response:
                status_code = int(response.status)
                response.read()
    except HTTPError as exc:
        metrics.increment("verification_code.failed")
        return VerificationCodeSendResult(sent=False, status_code=exc.code, error=_http_error_detail(exc))
    except (URLError, TimeoutError) as exc:
        metrics.increment("verification_code.failed")
        return VerificationCodeSendResult(sent=False, error=str(exc))

    if status_code >= 400:
        metrics.increment("verification_code.failed")
        return VerificationCodeSendResult(sent=False, status_code=status_code, error="whatsapp_send_failed")

    metrics.increment("verification_code.sent")
    return VerificationCodeSendResult(sent=True, status_code=status_code)


def _verification_template_payload(
    *,
    to: str,
    code: str,
    template_name: str,
    template_language: str,
) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": template_language},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": code}],
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": code}],
                },
            ],
        },
    }


def _http_error_detail(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return str(exc)
    meta_error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(meta_error, dict):
        return str(exc)
    parts = [
        str(part)
        for part in (
            meta_error.get("message"),
            meta_error.get("code"),
            meta_error.get("error_data", {}).get("details"),
        )
        if part
    ]
    return " | ".join(parts) if parts else str(exc)

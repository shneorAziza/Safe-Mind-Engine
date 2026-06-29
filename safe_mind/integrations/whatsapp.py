import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.core.config import settings
from safe_mind.core.metrics import metrics, timer
from safe_mind.integrations.parent_contacts import ParentContact


class WhatsAppSendResult(BaseModel):
    sent: bool
    skipped: bool = False
    status_code: int | None = None
    message_id: str | None = None
    error: str | None = None


def send_parent_whatsapp_alert(
    *,
    decision: ParentAlertDecision,
    contact: ParentContact,
    access_token: str | None = None,
    phone_number_id: str | None = None,
    template_name: str | None = None,
    template_language: str | None = None,
    graph_api_version: str | None = None,
) -> WhatsAppSendResult:
    resolved_token = access_token if access_token is not None else settings.whatsapp_access_token
    resolved_phone_number_id = (
        phone_number_id if phone_number_id is not None else settings.whatsapp_phone_number_id
    )
    resolved_template_name = template_name if template_name is not None else settings.whatsapp_template_name
    resolved_language = template_language if template_language is not None else settings.whatsapp_template_language
    resolved_version = graph_api_version if graph_api_version is not None else settings.whatsapp_graph_api_version

    missing = [
        name
        for name, value in (
            ("whatsapp_access_token", resolved_token),
            ("whatsapp_phone_number_id", resolved_phone_number_id),
            ("whatsapp_template_name", resolved_template_name),
        )
        if not value
    ]
    if missing:
        metrics.increment("whatsapp_alert.skipped")
        return WhatsAppSendResult(sent=False, skipped=True, error="missing_config:" + ",".join(missing))

    payload = _template_payload(
        to=contact.parent_phone,
        template_name=str(resolved_template_name),
        template_language=str(resolved_language),
        decision=decision,
    )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"https://graph.facebook.com/{resolved_version}/{resolved_phone_number_id}/messages",
        data=body,
        headers={
            "Authorization": f"Bearer {resolved_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    metrics.increment("whatsapp_alert.requests.total")
    try:
        with timer("whatsapp_alert.duration"):
            with urlopen(request, timeout=15) as response:
                status_code = int(response.status)
                response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error = str(exc)
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
            meta_error = error_payload.get("error") if isinstance(error_payload, dict) else None
            if isinstance(meta_error, dict):
                message = meta_error.get("message")
                code = meta_error.get("code")
                details = meta_error.get("error_data", {}).get("details")
                error_parts = [str(part) for part in (message, code, details) if part]
                if error_parts:
                    error = " | ".join(error_parts)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        metrics.increment("whatsapp_alert.failed")
        return WhatsAppSendResult(sent=False, status_code=exc.code, error=error)
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        metrics.increment("whatsapp_alert.failed")
        return WhatsAppSendResult(sent=False, error=str(exc))

    if status_code >= 400:
        metrics.increment("whatsapp_alert.failed")
        return WhatsAppSendResult(sent=False, status_code=status_code, error="whatsapp_send_failed")

    messages = response_payload.get("messages") if isinstance(response_payload, dict) else None
    message_id = None
    if isinstance(messages, list) and messages and isinstance(messages[0], dict):
        raw_id = messages[0].get("id")
        message_id = raw_id if isinstance(raw_id, str) else None

    metrics.increment("whatsapp_alert.sent")
    return WhatsAppSendResult(sent=True, status_code=status_code, message_id=message_id)


def _template_payload(
    *,
    to: str,
    template_name: str,
    template_language: str,
    decision: ParentAlertDecision,
) -> dict[str, Any]:
    components = _template_components(decision)
    template: dict[str, Any] = {
        "name": template_name,
        "language": {"code": template_language},
    }
    if components:
        template["components"] = components

    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }


def _template_components(decision: ParentAlertDecision) -> list[dict[str, Any]]:
    del decision
    return []

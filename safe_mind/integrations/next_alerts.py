import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.core.config import settings
from safe_mind.core.metrics import metrics, timer
from safe_mind.storage.models import NextIntegrationMapping


class AlertCallbackResult(BaseModel):
    sent: bool
    skipped: bool = False
    status_code: int | None = None
    error: str | None = None


def send_next_alert_callback(
    *,
    decision: ParentAlertDecision,
    mapping: NextIntegrationMapping,
    url: str | None = None,
    token: str | None = None,
) -> AlertCallbackResult:
    resolved_url = url if url is not None else settings.next_alert_callback_url
    resolved_token = token if token is not None else settings.next_alert_callback_token
    if not resolved_url:
        metrics.increment("next_alert_callback.skipped")
        return AlertCallbackResult(sent=False, skipped=True, error="callback_url_not_configured")

    payload = _alert_payload(decision=decision, mapping=mapping)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    request = Request(resolved_url, data=body, headers=headers, method="POST")
    metrics.increment("next_alert_callback.requests.total")
    try:
        with timer("next_alert_callback.duration"):
            with urlopen(request, timeout=15) as response:
                status_code = int(response.status)
    except HTTPError as exc:
        metrics.increment("next_alert_callback.failed")
        return AlertCallbackResult(sent=False, status_code=exc.code, error=str(exc))
    except URLError as exc:
        metrics.increment("next_alert_callback.failed")
        return AlertCallbackResult(sent=False, error=str(exc.reason))
    except TimeoutError as exc:
        metrics.increment("next_alert_callback.failed")
        return AlertCallbackResult(sent=False, error=str(exc))

    if status_code >= 400:
        metrics.increment("next_alert_callback.failed")
        return AlertCallbackResult(sent=False, status_code=status_code, error="callback_failed")
    metrics.increment("next_alert_callback.sent")
    return AlertCallbackResult(sent=True, status_code=status_code)


def _alert_payload(
    *,
    decision: ParentAlertDecision,
    mapping: NextIntegrationMapping,
) -> dict[str, Any]:
    alert_id = uuid5(
        NAMESPACE_URL,
        f"safe-mind-alert:{decision.child_user_id}:{decision.target_day.isoformat()}",
    )
    return {
        "alertId": str(alert_id),
        "uid": mapping.uid,
        "deviceId": mapping.external_device_id,
        "childUserId": str(decision.child_user_id),
        "internalDeviceId": str(mapping.device_id),
        "targetDay": decision.target_day.isoformat(),
        "shouldSendPush": decision.should_send_push,
        "reason": decision.reason,
        "deviationsInWindow": decision.deviations_in_window,
        "gateWindowDays": decision.gate_window_days,
        "requiredDeviationDays": decision.required_deviation_days,
        "messageCount": decision.message_count,
    }

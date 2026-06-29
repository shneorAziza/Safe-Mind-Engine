from datetime import date
from uuid import UUID

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.integrations.whatsapp import _template_payload


def test_template_payload_uses_configured_template_and_parent_phone() -> None:
    decision = ParentAlertDecision(
        child_user_id=UUID("fd588728-5478-44c7-b887-673581a571bc"),
        target_day=date(2026, 6, 24),
        should_send_push=True,
        reason="loneliness +3 from baseline",
        deviations_in_window=3,
        gate_window_days=3,
        required_deviation_days=3,
        message_count=7,
    )

    payload = _template_payload(
        to="+972501234567",
        template_name="safe_mind_alert",
        template_language="he",
        decision=decision,
    )

    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "+972501234567"
    assert payload["type"] == "template"
    assert payload["template"]["name"] == "safe_mind_alert"
    assert payload["template"]["language"]["code"] == "he"

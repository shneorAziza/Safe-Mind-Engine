from datetime import UTC, date, datetime
from uuid import UUID

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.integrations.next_alerts import _alert_payload
from safe_mind.storage.models import NextIntegrationMapping


def test_alert_payload_uses_next_identifiers() -> None:
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
    mapping = NextIntegrationMapping(
        child_user_id=decision.child_user_id,
        device_id=UUID("1736d0fe-f1a4-410e-bca2-696d36c029c3"),
        uid="firebase-user-id",
        external_device_id="firestore-device-id",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    payload = _alert_payload(decision=decision, mapping=mapping)

    assert payload["uid"] == "firebase-user-id"
    assert payload["deviceId"] == "firestore-device-id"
    assert payload["targetDay"] == "2026-06-24"
    assert payload["shouldSendPush"] is True
    assert payload["messageCount"] == 7
    assert payload["alertId"]

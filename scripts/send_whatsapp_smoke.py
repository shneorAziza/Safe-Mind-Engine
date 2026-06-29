from datetime import date
import sys
from uuid import UUID

from safe_mind.alerts.models import ParentAlertDecision
from safe_mind.integrations.parent_contacts import ParentContact
from safe_mind.integrations.whatsapp import send_parent_whatsapp_alert


def main() -> None:
    parent_phone = sys.argv[1] if len(sys.argv) > 1 else "+972509845430"
    decision = ParentAlertDecision(
        child_user_id=UUID("fd588728-5478-44c7-b887-673581a571bc"),
        target_day=date.today(),
        should_send_push=True,
        reason="בדיקת מערכת SafeMind",
        deviations_in_window=3,
        gate_window_days=3,
        required_deviation_days=3,
        message_count=7,
    )
    contact = ParentContact(uid="smoke-test", parent_phone=parent_phone)
    result = send_parent_whatsapp_alert(decision=decision, contact=contact)
    print(result.model_dump_json(exclude_none=True))


if __name__ == "__main__":
    main()

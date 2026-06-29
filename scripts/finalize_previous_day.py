import argparse
import json
from datetime import date, datetime

from safe_mind.alerts.finalization_job import run_daily_finalization


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize closed-day SafeMind alert decisions.")
    parser.add_argument(
        "--target-day",
        type=date.fromisoformat,
        default=None,
        help="Closed day to finalize in YYYY-MM-DD format. Defaults to the previous UTC day.",
    )
    parser.add_argument(
        "--run-at",
        type=datetime.fromisoformat,
        default=None,
        help="Optional run timestamp for testing previous-day resolution.",
    )
    parser.add_argument(
        "--send-alerts",
        action="store_true",
        help="Send outbound WhatsApp alerts for finalized parent-alert decisions.",
    )
    args = parser.parse_args()

    summary = run_daily_finalization(
        target_day=args.target_day,
        run_at=args.run_at,
        send_alerts=args.send_alerts,
    )
    print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

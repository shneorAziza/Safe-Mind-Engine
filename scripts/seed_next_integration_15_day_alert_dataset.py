import argparse
from datetime import UTC, date, datetime, time, timedelta

from safe_mind.api.next_integration import NextBatchIngestRequest, NextMessage, ingest_next_messages
from safe_mind.core.config import settings


DEVICE_ID = "safe-mind-e2e-test-device"

BASELINE_MESSAGES = (
    "Can you help me organize my math homework for tonight?",
    "I want to practice English vocabulary before class tomorrow.",
    "Please help me make a short plan for my science notes.",
)

FOLLOWUP_MESSAGES = (
    "I feel a little stressed about school, but I want help making a calm plan.",
    "I am tired after class and want to organize homework before dinner.",
    "Can you quiz me gently so I feel ready for tomorrow?",
)

ALERT_MESSAGES = (
    "I feel completely alone today, like nobody notices when I am struggling.",
    "I keep thinking I am worthless and nothing I do is good enough.",
    "I feel hopeless tonight and I do not know how to get through this feeling.",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a 15-day SafeMind E2E alert dataset through /v1/integrations/next/messages."
    )
    parser.add_argument("--uid", default="safe-mind-e2e-test-parent")
    parser.add_argument("--device-id", default=DEVICE_ID)
    parser.add_argument("--target-day", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--configured-provider",
        action="store_true",
        help="Use the configured analyzer provider. By default this forces heuristic scoring for deterministic smoke tests.",
    )
    args = parser.parse_args()

    if not args.configured_provider:
        settings.psychological_analyzer_provider = "heuristic"
    settings.enable_embeddings = False
    settings.persist_signals = True

    start_day = args.target_day - timedelta(days=14)
    accepted = 0
    for day_index in range(1, 16):
        day = start_day + timedelta(days=day_index - 1)
        messages = [
            NextMessage(
                messageId=f"safe-mind-e2e-{args.uid}-{day.isoformat()}-{message_index}",
                text=text,
                timestamp=int(
                    datetime.combine(
                        day,
                        time(9 + message_index, 15, tzinfo=UTC),
                    ).timestamp()
                    * 1000
                ),
                sourceApp="safe-mind-e2e-synthetic",
                locale="en",
            )
            for message_index, text in enumerate(_messages_for_day(day_index), start=1)
        ]
        payload = NextBatchIngestRequest(
            uid=args.uid,
            deviceId=args.device_id,
            messages=messages,
        )
        result = ingest_next_messages(payload, authorization=None)
        accepted += result.accepted
        print(f"day={day.isoformat()} day_index={day_index} accepted={result.accepted}", flush=True)

    print(f"uid={args.uid}")
    print(f"device_id={args.device_id}")
    print(f"start_day={start_day.isoformat()}")
    print(f"target_day={args.target_day.isoformat()}")
    print(f"messages_accepted={accepted}")
    print("expected_alert_day_index=15")


def _messages_for_day(day_index: int) -> tuple[str, str, str]:
    if day_index <= 10:
        return BASELINE_MESSAGES
    if day_index in {13, 14, 15}:
        return ALERT_MESSAGES
    return FOLLOWUP_MESSAGES


if __name__ == "__main__":
    main()

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SafeMind pipeline with full debug logs.")
    parser.add_argument("--text", action="append", help="Text to process. Can be passed multiple times.")
    parser.add_argument("--file", help="UTF-8 text file with one message per line.")
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Run analysis and logs, but do not save signal features to the local store.",
    )
    parser.add_argument(
        "--no-vector",
        action="store_true",
        help="Compatibility flag. Embeddings are disabled unless SAFE_MIND_ENABLE_EMBEDDINGS=true.",
    )
    args = parser.parse_args()

    texts = list(args.text or [])
    if args.file:
        texts.extend(
            line.strip()
            for line in Path(args.file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    if not texts:
        raise SystemExit("Provide --text or --file.")

    outputs = []
    for text in texts:
        payload = IngestMessageRequest(
            event_id=uuid4(),
            child_user_id=uuid4(),
            device_id=uuid4(),
            occurred_at=datetime.now(UTC),
            source_type="manual",
            source_app="debug",
            text=text,
            locale="he",
        )
        result = process_message(
            payload,
            debug=True,
            persist=not args.no_persist,
            create_vector=not args.no_vector,
        )
        outputs.append(
            {
                "event_id": str(payload.event_id),
                "stored_signal": result.stored_signal.model_dump(),
                "logs": [entry.model_dump() for entry in result.logs],
            }
        )

    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

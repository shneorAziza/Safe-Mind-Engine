import json
from pathlib import Path
from typing import Any

from safe_mind.privacy.redactor import redact_text
from safe_mind.signals.service import run_emotional_filter

DATASET_PATH = Path("data/filter_eval_cases.jsonl")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                cases.append(json.loads(line))
    return cases


def main() -> None:
    cases = load_cases(DATASET_PATH)
    passed_cases: list[dict[str, Any]] = []
    missed_cases: list[dict[str, Any]] = []
    wrongly_passed_cases: list[dict[str, Any]] = []

    for case in cases:
        redaction = redact_text(case["text"])
        result = run_emotional_filter(redaction.redacted_text)
        expected = case["expected"]

        actual = result.model_dump()
        item = {
            "id": case["id"],
            "text": case["text"],
            "should_pass": expected["is_emotionally_relevant"],
            "passed": actual["is_emotionally_relevant"],
            "confidence": actual["confidence"],
            "provider": actual["provider"],
        }

        if actual["is_emotionally_relevant"]:
            passed_cases.append(item)
        if expected["is_emotionally_relevant"] and not actual["is_emotionally_relevant"]:
            missed_cases.append(item)
        if not expected["is_emotionally_relevant"] and actual["is_emotionally_relevant"]:
            wrongly_passed_cases.append(item)

    total = len(cases)
    expected_relevant_count = sum(1 for case in cases if case["expected"]["is_emotionally_relevant"])
    correctly_passed_count = sum(1 for item in passed_cases if item["should_pass"])

    print(
        json.dumps(
            {
                "total": total,
                "should_pass_count": expected_relevant_count,
                "passed_count": len(passed_cases),
                "correctly_passed_count": correctly_passed_count,
                "missed_count": len(missed_cases),
                "wrongly_passed_count": len(wrongly_passed_cases),
                "passed_cases": passed_cases,
                "missed_cases": missed_cases,
                "wrongly_passed_cases": wrongly_passed_cases,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

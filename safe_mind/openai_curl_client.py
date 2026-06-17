import json
import subprocess
from typing import Any


class CurlOpenAIError(RuntimeError):
    pass


def post_json(path: str, *, api_key: str, payload: dict[str, Any], timeout_seconds: int = 60) -> dict[str, Any]:
    command = [
        "curl.exe",
        "-sS",
        "--http1.1",
        "--connect-timeout",
        "15",
        "--max-time",
        str(timeout_seconds),
        "-X",
        "POST",
        f"https://api.openai.com{path}",
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload, ensure_ascii=False),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise CurlOpenAIError(stderr or f"curl exited with code {completed.returncode}")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CurlOpenAIError("OpenAI curl response was not valid JSON.") from exc

    if isinstance(data, dict) and "error" in data:
        raise CurlOpenAIError(json.dumps(data["error"], ensure_ascii=False))

    return data

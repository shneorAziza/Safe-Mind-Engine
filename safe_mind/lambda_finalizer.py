from datetime import datetime
from typing import Any

from safe_mind.alerts.finalization_job import run_daily_finalization


def handler(event: dict[str, Any] | None, context: object) -> dict[str, Any]:
    del context
    payload = event or {}
    target_day = payload.get("target_day")
    run_at = payload.get("time") or payload.get("run_at")
    summary = run_daily_finalization(
        target_day=datetime.fromisoformat(target_day).date() if target_day else None,
        run_at=_parse_datetime(run_at) if run_at else None,
        send_alerts=bool(payload.get("send_alerts", True)),
    )
    return summary.model_dump(mode="json")


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

from typing import Any

from fastapi import APIRouter

from safe_mind.core.metrics import metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics_snapshot() -> dict[str, Any]:
    return metrics.snapshot()

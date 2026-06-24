from fastapi import APIRouter, HTTPException, status

from safe_mind.core.config import settings
from safe_mind.storage.factory import get_signal_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "safe_mind"}


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    return {"status": "ok", "service": "safe_mind"}


@router.get("/health/ready")
def readiness_check() -> dict[str, object]:
    checks: dict[str, object] = {
        "env": settings.env,
        "signal_store_provider": settings.signal_store_provider,
    }
    try:
        if settings.env.lower() == "production" and settings.signal_store_provider != "mongodb":
            raise RuntimeError("Signal store provider must be mongodb in production.")
        store = get_signal_store()
        store.ping()
        checks["storage"] = "ok"
    except Exception as exc:
        checks["storage"] = {
            "status": "error",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks,
        ) from exc

    return {
        "status": "ready",
        "service": "safe_mind",
        "checks": checks,
    }

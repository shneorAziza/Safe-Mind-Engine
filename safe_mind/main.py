from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from time import perf_counter

from fastapi import FastAPI, Request

from safe_mind.api.app_auth import router as app_auth_router
from safe_mind.api.eval_ui import router as eval_ui_router
from safe_mind.api.health import router as health_router
from safe_mind.api.ingestion import router as ingestion_router
from safe_mind.api.metrics import router as metrics_router
from safe_mind.api.next_integration import router as next_integration_router
from safe_mind.core.config import settings, validate_production_settings
from safe_mind.core.metrics import metrics
from safe_mind.storage.factory import get_signal_store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    validate_production_settings()
    get_signal_store().initialize()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.api_title, lifespan=lifespan)

    @app.middleware("http")
    async def record_http_metrics(request: Request, call_next):
        started_at = perf_counter()
        response = await call_next(request)
        elapsed_ms = (perf_counter() - started_at) * 1000
        route = request.url.path
        method = request.method
        status_family = f"{response.status_code // 100}xx"
        metrics.increment("http.requests.total")
        metrics.increment(f"http.requests.{method}.{route}.{status_family}")
        metrics.observe_ms("http.request.duration", elapsed_ms)
        return response

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(app_auth_router)
    app.include_router(ingestion_router)
    app.include_router(next_integration_router)
    app.include_router(eval_ui_router)
    return app


app = create_app()

from fastapi import FastAPI

from safe_mind.api.eval_ui import router as eval_ui_router
from safe_mind.api.health import router as health_router
from safe_mind.api.ingestion import router as ingestion_router
from safe_mind.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.api_title)
    app.include_router(health_router)
    app.include_router(ingestion_router)
    app.include_router(eval_ui_router)
    return app


app = create_app()

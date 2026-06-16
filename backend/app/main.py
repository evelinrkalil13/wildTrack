from fastapi import FastAPI

from app.lifespan import lifespan
from infrastructure.health import router as health_router
from shared.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="WildTrack API",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.include_router(health_router)

    return app


app = create_app()

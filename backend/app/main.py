from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.lifespan import lifespan
from infrastructure.health import router as health_router
from modules.auth.router import router as auth_router
from modules.stations.router import router as stations_router
from modules.zones.router import router as zones_router
from shared.base_exception import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    WildTrackException,
)
from shared.config import get_settings


def _http_status(exc: WildTrackException) -> int:
    if isinstance(exc, NotFoundError):
        return 404
    if isinstance(exc, ConflictError):
        return 409
    if isinstance(exc, ForbiddenError):
        return 403
    if isinstance(exc, UnauthorizedError):
        return 401
    return 400


async def _wildtrack_exception_handler(request: Request, exc: WildTrackException) -> JSONResponse:
    return JSONResponse(
        status_code=_http_status(exc),
        content={"error": exc.code, "message": exc.message},
    )


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="WildTrack API",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_exception_handler(WildTrackException, _wildtrack_exception_handler)

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(zones_router, prefix="/api/v1")
    app.include_router(stations_router, prefix="/api/v1")

    return app


app = create_app()

"""CrowdVision Heatmap Engine — FastAPI application entrypoint.

Wires the routers, database, camera manager and background persistence loop
together behind a clean lifespan context.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import analytics, camera, health, location, stream
from app.core.config import get_settings
from app.core.logger import configure_logging, get_logger
from app.database.session import init_db
from app.services.camera_service import get_camera_manager
from app.services.storage_service import get_storage_service, persistence_loop

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s (%s)", settings.app_name, __version__, settings.environment)

    storage = get_storage_service()

    # Database — best-effort so the engine still boots for demos without a DB.
    try:
        await init_db()
        logger.info("Database initialised")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Database unavailable (%s); analytics persistence disabled. The live "
            "heatmap works without a database.",
            exc,
        )
        storage._db_ok = False  # skip DB writes entirely this session

    await storage.connect_redis()
    manager = get_camera_manager()

    stop_event = asyncio.Event()
    task = asyncio.create_task(persistence_loop(manager, storage, stop_event))

    app.state.stop_event = stop_event
    app.state.persistence_task = task

    try:
        yield
    finally:
        logger.info("Shutting down…")
        stop_event.set()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        manager.shutdown()
        await storage.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "AI-powered crowd heatmap microservice: YOLOv11 detection, "
            "ByteTrack tracking, Gaussian KDE density and live heatmap streaming."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(camera.router, prefix=prefix)
    app.include_router(analytics.router, prefix=prefix)
    app.include_router(location.router, prefix=prefix)
    app.include_router(stream.router, prefix=prefix)

    @app.get("/")
    async def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": settings.app_name,
                "version": __version__,
                "docs": "/docs",
                "health": f"{prefix}/health",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

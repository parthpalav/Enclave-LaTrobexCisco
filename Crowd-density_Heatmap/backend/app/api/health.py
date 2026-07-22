"""Health/readiness endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app import __version__
from app.core.config import Settings, get_settings
from app.database.schemas import HealthOut
from app.models.yolo_detector import resolve_device
from app.services.camera_service import CameraManager, get_camera_manager

router = APIRouter(tags=["health"])
_START_TIME = time.time()


@router.get("/health", response_model=HealthOut)
async def health(
    settings: Settings = Depends(get_settings),
    manager: CameraManager = Depends(get_camera_manager),
) -> HealthOut:
    """Liveness/readiness probe with basic runtime facts."""
    return HealthOut(
        status="ok",
        version=__version__,
        environment=settings.environment,
        device=resolve_device(settings.yolo_device),
        cameras_active=manager.active_count,
        uptime_seconds=round(time.time() - _START_TIME, 1),
    )

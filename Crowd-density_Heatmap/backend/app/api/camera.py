"""Camera management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.logger import get_logger
from app.database.schemas import CameraCreate, CameraStatus
from app.services.camera_service import (
    CameraLimitReached,
    CameraManager,
    CameraNotFound,
    get_camera_manager,
)
from app.services.storage_service import StorageService, get_storage_service

logger = get_logger(__name__)
router = APIRouter(prefix="/camera", tags=["camera"])


class CameraRemove(BaseModel):
    camera_id: str


@router.post("/add", response_model=CameraStatus, status_code=status.HTTP_201_CREATED)
async def add_camera(
    payload: CameraCreate,
    manager: CameraManager = Depends(get_camera_manager),
    storage: StorageService = Depends(get_storage_service),
) -> CameraStatus:
    """Register a camera and start its real-time heatmap pipeline."""
    crowd_thresholds = {
        "moderate": payload.crowd_moderate_threshold,
        "crowded": payload.crowd_crowded_threshold,
        "overcrowded": payload.crowd_overcrowded_threshold,
    }
    try:
        pipeline = manager.add(payload.camera_id, payload.source, crowd_thresholds)
    except CameraLimitReached as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    await storage.upsert_camera(
        {
            "camera_id": payload.camera_id,
            "name": payload.name,
            "source": payload.source,
            "location": payload.location,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "enabled": payload.enabled,
        }
    )
    return CameraStatus(**pipeline.snapshot_status())


@router.post("/remove", status_code=status.HTTP_200_OK)
async def remove_camera(
    payload: CameraRemove,
    manager: CameraManager = Depends(get_camera_manager),
    storage: StorageService = Depends(get_storage_service),
) -> dict:
    """Stop a camera pipeline and delete its metadata."""
    try:
        manager.remove(payload.camera_id)
    except CameraNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found") from exc
    await storage.delete_camera(payload.camera_id)
    return {"status": "removed", "camera_id": payload.camera_id}


@router.get("/list", response_model=list[CameraStatus])
async def list_cameras(
    manager: CameraManager = Depends(get_camera_manager),
) -> list[CameraStatus]:
    """List all active camera pipelines and their live status."""
    return [CameraStatus(**s) for s in manager.statuses()]

"""Crowd analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.schemas import AlertOut, AnalyticsOut
from app.services.camera_service import CameraManager, get_camera_manager
from app.services.storage_service import StorageService, get_storage_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/current")
async def current_analytics(
    camera_id: str = Query(..., description="Camera identifier"),
    manager: CameraManager = Depends(get_camera_manager),
    storage: StorageService = Depends(get_storage_service),
) -> dict:
    """Return the most recent analytics for a camera (live, in-memory first)."""
    pipeline = manager.get_optional(camera_id)
    if pipeline is not None:
        latest = pipeline.latest_analytics()
        if latest:
            return {**latest, "fps": pipeline.snapshot_status()["fps"]}

    cached = await storage.get_cached_latest(camera_id)
    if cached:
        return cached
    raise HTTPException(status.HTTP_404_NOT_FOUND, "No analytics available yet")


@router.get("/history", response_model=list[AnalyticsOut])
async def analytics_history(
    camera_id: str = Query(...),
    minutes: int = Query(60, ge=1, le=1440),
    limit: int = Query(500, ge=1, le=5000),
    storage: StorageService = Depends(get_storage_service),
) -> list[AnalyticsOut]:
    """Return historical analytics for a camera over the last N minutes."""
    rows = await storage.analytics_history(camera_id, minutes=minutes, limit=limit)
    return [AnalyticsOut.model_validate(r) for r in rows]


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    camera_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    storage: StorageService = Depends(get_storage_service),
) -> list[AlertOut]:
    """Return recent crowd alerts, optionally filtered by camera."""
    rows = await storage.list_alerts(camera_id=camera_id, limit=limit)
    return [AlertOut.model_validate(r) for r in rows]

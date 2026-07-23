"""Live streaming endpoints: latest heatmap, MJPEG and WebSocket."""

from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.logger import get_logger
from app.database.schemas import HeatmapOut
from app.services.camera_service import CameraManager, get_camera_manager

logger = get_logger(__name__)
router = APIRouter(tags=["stream"])
settings = get_settings()


@router.get("/heatmap/latest", response_model=HeatmapOut)
async def latest_heatmap(
    camera_id: str = Query(...),
    manager: CameraManager = Depends(get_camera_manager),
) -> HeatmapOut:
    """Return the latest heatmap overlay as a base64 JPEG data-URI."""
    pipeline = manager.get_optional(camera_id)
    if pipeline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    jpeg = pipeline.latest_overlay_jpeg()
    if jpeg is None:
        raise HTTPException(status.HTTP_425_TOO_EARLY, "No frame processed yet")

    latest = pipeline.latest_analytics() or {}
    b64 = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
    return HeatmapOut(
        camera_id=camera_id,
        timestamp=latest.get("timestamp", 0.0),
        image=b64,
        people_count=latest.get("people_count", 0),
        max_density=latest.get("max_density", 0.0),
    )


def _mjpeg_generator(pipeline, kind: str, fps: int):
    boundary = b"--frame"
    period = 1.0 / max(1, fps)
    import time as _time

    while pipeline.running:
        jpeg = (
            pipeline.latest_overlay_jpeg()
            if kind == "overlay"
            else pipeline.latest_raw_jpeg()
        )
        if jpeg is not None:
            yield (
                boundary
                + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                + str(len(jpeg)).encode()
                + b"\r\n\r\n"
                + jpeg
                + b"\r\n"
            )
        _time.sleep(period)


@router.get("/stream/mjpeg")
async def stream_mjpeg(
    camera_id: str = Query(...),
    kind: str = Query("overlay", pattern="^(overlay|raw)$"),
    manager: CameraManager = Depends(get_camera_manager),
):
    """MJPEG stream of the heatmap overlay (or raw preview). Browser-native."""
    pipeline = manager.get_optional(camera_id)
    if pipeline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    return StreamingResponse(
        _mjpeg_generator(pipeline, kind, settings.target_fps),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.websocket("/stream/live")
async def stream_live(websocket: WebSocket) -> None:
    """WebSocket stream of {analytics + base64 heatmap} frames.

    Query params: ``camera_id`` (required), ``fps`` (optional cap),
    ``include_image`` ('1' default; '0' for analytics-only),
    ``include_raw`` ('1' to also stream the original camera preview — same
    transport as the heatmap, so both panes stay in sync and reconnect together).
    """
    await websocket.accept()
    manager: CameraManager = get_camera_manager()

    camera_id = websocket.query_params.get("camera_id")
    include_image = websocket.query_params.get("include_image", "1") != "0"
    include_raw = websocket.query_params.get("include_raw", "0") != "0"
    try:
        fps = int(websocket.query_params.get("fps", settings.target_fps))
    except ValueError:
        fps = settings.target_fps
    period = 1.0 / max(1, min(fps, settings.target_fps))

    if not camera_id:
        await websocket.send_json({"error": "camera_id query param is required"})
        await websocket.close()
        return

    pipeline = manager.get_optional(camera_id)
    if pipeline is None:
        await websocket.send_json({"error": "camera not found"})
        await websocket.close()
        return

    logger.info("WebSocket client connected for camera '%s'", camera_id)
    last_ts = None
    try:
        while True:
            payload = pipeline.latest_analytics()
            status_info = pipeline.snapshot_status()
            if payload and payload.get("timestamp") != last_ts:
                last_ts = payload.get("timestamp")
                message = {
                    "type": "frame",
                    "status": status_info,
                    "analytics": payload,
                }
                if include_image:
                    jpeg = pipeline.latest_overlay_jpeg()
                    if jpeg is not None:
                        message["image"] = (
                            "data:image/jpeg;base64,"
                            + base64.b64encode(jpeg).decode("ascii")
                        )
                if include_raw:
                    raw = pipeline.latest_raw_jpeg()
                    if raw is not None:
                        message["raw_image"] = (
                            "data:image/jpeg;base64,"
                            + base64.b64encode(raw).decode("ascii")
                        )
                await websocket.send_json(message)
            await asyncio.sleep(period)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for camera '%s'", camera_id)
    except Exception:  # noqa: BLE001
        logger.exception("WebSocket error for camera '%s'", camera_id)
        await websocket.close()

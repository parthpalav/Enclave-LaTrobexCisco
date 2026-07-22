"""Pydantic request/response schemas (API contract)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Camera
# --------------------------------------------------------------------------- #
class CameraCreate(BaseModel):
    camera_id: str = Field(..., examples=["cam-01"], max_length=64)
    name: str = Field(..., examples=["Main Gate"])
    source: str = Field(
        ...,
        description="RTSP/HTTP stream URL, local file path, or webcam index (e.g. '0').",
        examples=["rtsp://user:pass@192.168.1.10:554/stream1"],
    )
    location: str | None = Field(default=None, examples=["North Entrance"])
    latitude: float | None = None
    longitude: float | None = None
    enabled: bool = True

    # Optional per-camera crowd thresholds (people count). None → use server
    # defaults from configuration.
    crowd_moderate_threshold: int | None = Field(default=None, ge=1)
    crowd_crowded_threshold: int | None = Field(default=None, ge=1)
    crowd_overcrowded_threshold: int | None = Field(default=None, ge=1)


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    camera_id: str
    name: str
    source: str
    location: str | None
    latitude: float | None
    longitude: float | None
    enabled: bool
    created_at: datetime


class CameraStatus(BaseModel):
    camera_id: str
    running: bool
    connected: bool
    fps: float
    people_count: int
    last_frame_at: float | None = None


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #
class CrowdedZone(BaseModel):
    x: float
    y: float
    radius: float
    intensity: float


class AnalyticsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    camera_id: str
    timestamp: datetime
    people_count: int
    density_score: float
    average_density: float
    max_density: float
    crowd_level: str = "low"
    crowded_zones: list[dict] = []
    movement_index: float = 0.0
    fps: float = 0.0


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: str
    timestamp: datetime
    level: str
    kind: str
    message: str
    people_count: int
    max_density: float
    acknowledged: bool


# --------------------------------------------------------------------------- #
# Heatmap
# --------------------------------------------------------------------------- #
class HeatmapOut(BaseModel):
    camera_id: str
    timestamp: float
    image: str = Field(..., description="Base64 JPEG data-URI of the heatmap overlay.")
    people_count: int
    max_density: float


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
    device: str
    cameras_active: int
    uptime_seconds: float

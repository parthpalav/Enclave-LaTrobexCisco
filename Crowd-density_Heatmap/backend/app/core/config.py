"""Application configuration.

All values are loaded from environment variables (or an `.env` file).
Nothing is hardcoded — every tunable is exposed here so the engine can be
reconfigured without touching code, per the project's coding standards.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    app_name: str = Field(default="CrowdVision Heatmap Engine")
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    api_prefix: str = Field(default="/api/v1")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: str = Field(default="*", description="Comma-separated list of origins")

    # ------------------------------------------------------------------ #
    # Database (PostgreSQL)
    # ------------------------------------------------------------------ #
    database_url: str = Field(
        default="postgresql+asyncpg://crowdvision:crowdvision@localhost:5432/crowdvision"
    )
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_echo: bool = Field(default=False)

    # ------------------------------------------------------------------ #
    # Redis (pub/sub + caching of latest frames/analytics)
    # ------------------------------------------------------------------ #
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_ttl_seconds: int = Field(default=60)

    # ------------------------------------------------------------------ #
    # Detection model (YOLO)
    # ------------------------------------------------------------------ #
    yolo_model: str = Field(
        default="yolo11m.pt",
        description="Primary model weights (YOLOv11 Medium for high accuracy).",
    )
    yolo_fallback_model: str = Field(
        default="yolov8m.pt",
        description="Fallback weights if the primary fails to load.",
    )
    yolo_device: str = Field(
        default="auto",
        description="'auto' | 'cpu' | 'cuda' | 'cuda:0' — auto detects CUDA.",
    )
    yolo_confidence: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        description="Low confidence threshold to detect small, distant, or occluded crowd members.",
    )
    yolo_iou: float = Field(default=0.55, ge=0.0, le=1.0)
    yolo_imgsz: int = Field(
        default=1024,
        description="Higher inference resolution (1024px) for detecting distant crowd faces/bodies.",
    )
    person_class_id: int = Field(default=0, description="COCO class id for 'person'.")
    yolo_max_det: int = Field(
        default=1000,
        description="Max detections per frame. High cap for dense crowds.",
    )
    yolo_half_precision: bool = Field(
        default=False, description="Use FP16 on CUDA for throughput."
    )

    # ------------------------------------------------------------------ #
    # Tracking (ByteTrack)
    # ------------------------------------------------------------------ #
    tracker_config: str = Field(
        default="bytetrack.yaml",
        description="Ultralytics tracker config (ByteTrack by default).",
    )

    # ------------------------------------------------------------------ #
    # Heatmap / Gaussian density
    # ------------------------------------------------------------------ #
    heatmap_sigma: float = Field(
        default=55.0, description="Gaussian kernel sigma (spread of each person)."
    )
    heatmap_kernel_size: int = Field(
        default=0,
        description="Explicit kernel size in px; 0 = derive from sigma (6*sigma+1).",
    )
    heatmap_alpha: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Peak overlay opacity (dense areas)."
    )
    heatmap_base_alpha: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description=(
            "Baseline overlay opacity in sparse areas. >0 gives a full-frame blue "
            "wash (like classic CCTV heatmaps); 0 leaves empty areas transparent."
        ),
    )
    heatmap_downscale: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Compute density at a fraction of frame size for speed.",
    )
    heatmap_min_density: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="Normalized density below this stays fully transparent.",
    )
    heatmap_colormap: str = Field(
        default="jet",
        description="'crowdvision' (blue→green→yellow→orange→red), 'jet' or an OpenCV name.",
    )
    heatmap_mode: str = Field(
        default="pure",
        description=(
            "'overlay' blends the heatmap over the camera image; 'pure' renders a "
            "standalone abstract heatmap (grey where empty, no faces/visuals)."
        ),
    )
    density_mode: str = Field(
        default="box",
        description=(
            "How each person contributes density: 'foot' (ground point), 'center', "
            "or 'box' (the whole detection area — colours the person's body region)."
        ),
    )
    heatmap_grid: bool = Field(
        default=True, description="Draw a faint reference grid (pure mode only)."
    )
    heatmap_grid_size: int = Field(
        default=32, description="Grid cell size in pixels."
    )
    density_high_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Normalized density above which a zone is 'crowded'.",
    )

    # ------------------------------------------------------------------ #
    # Streaming / processing
    # ------------------------------------------------------------------ #
    target_fps: int = Field(default=25)
    frame_width: int = Field(default=1280)
    frame_height: int = Field(default=720)
    jpeg_quality: int = Field(default=80, ge=1, le=100)
    max_cameras: int = Field(default=8)
    analytics_persist_interval: int = Field(
        default=25,
        description="Persist analytics to the DB every N frames (throttle writes).",
    )
    store_raw_video: bool = Field(
        default=False, description="NEVER store raw CCTV unless explicitly enabled."
    )

    # ------------------------------------------------------------------ #
    # Crowd-level classification (by people count)
    # ------------------------------------------------------------------ #
    crowd_moderate_threshold: int = Field(
        default=3, description="People count at/above which the scene is 'Moderate'."
    )
    crowd_crowded_threshold: int = Field(
        default=6, description="People count at/above which the scene is 'Crowded'."
    )
    crowd_overcrowded_threshold: int = Field(
        default=12,
        description="People count at/above which the scene is 'Overcrowded'.",
    )

    # ------------------------------------------------------------------ #
    # Alerts
    # ------------------------------------------------------------------ #
    alert_people_threshold: int = Field(
        default=6, description="People count that triggers a crowd alert."
    )
    alert_density_threshold: float = Field(
        default=0.75, ge=0.0, le=1.0, description="Max density that triggers an alert."
    )

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False, description="Emit structured JSON logs.")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor used for dependency injection."""
    return Settings()

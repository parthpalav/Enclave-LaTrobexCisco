"""Per-camera processing pipeline and streaming helpers.

Each :class:`CameraPipeline` owns one camera end-to-end:

    capture → YOLO detect → ByteTrack → density (Gaussian KDE)
            → heatmap overlay → encode → publish latest frame/analytics

The heavy CV/AI work is blocking, so each pipeline runs in its own daemon
thread. The latest processed JPEG and analytics are published behind a lock for
the async API/WebSocket layer to read without blocking the event loop.
"""

from __future__ import annotations

import threading
import time
from dataclasses import asdict

import cv2
import numpy as np

from app.core.config import Settings
from app.core.logger import get_logger
from app.models.density import DensityEstimator
from app.models.heatmap import HeatmapGenerator
from app.models.tracker import MovementTracker
from app.models.yolo_detector import YoloDetector
from app.services.analytics_service import AnalyticsComputer
from app.utils.image import encode_jpeg, resize_keep

logger = get_logger(__name__)


def _parse_source(source: str):
    """Interpret a source string as a webcam index or a URL/path."""
    s = source.strip()
    if s.isdigit():
        return int(s)
    return s


class CameraPipeline:
    """Runs the full heatmap pipeline for a single camera."""

    def __init__(
        self,
        camera_id: str,
        source: str,
        settings: Settings,
        crowd_thresholds: dict | None = None,
    ):
        self.camera_id = camera_id
        self.source = source
        self.settings = settings
        # Resolve per-camera crowd thresholds, falling back to server defaults.
        ct = crowd_thresholds or {}
        self.crowd_moderate = ct.get("moderate") or settings.crowd_moderate_threshold
        self.crowd_crowded = ct.get("crowded") or settings.crowd_crowded_threshold
        self.crowd_overcrowded = (
            ct.get("overcrowded") or settings.crowd_overcrowded_threshold
        )

        # Pipeline components (each camera keeps isolated tracker state).
        self.detector = YoloDetector(
            model_path=settings.yolo_model,
            fallback_path=settings.yolo_fallback_model,
            device=settings.yolo_device,
            confidence=settings.yolo_confidence,
            iou=settings.yolo_iou,
            imgsz=settings.yolo_imgsz,
            person_class_id=settings.person_class_id,
            tracker_config=settings.tracker_config,
            half=settings.yolo_half_precision,
        )
        self.movement = MovementTracker()
        self.density = DensityEstimator(
            sigma=settings.heatmap_sigma,
            kernel_size=settings.heatmap_kernel_size,
            downscale=settings.heatmap_downscale,
            source=settings.density_mode,
        )
        self.heatmap = HeatmapGenerator(
            alpha=settings.heatmap_alpha,
            min_density=settings.heatmap_min_density,
            colormap=settings.heatmap_colormap,
            base_alpha=settings.heatmap_base_alpha,
            mode=settings.heatmap_mode,
            grid=settings.heatmap_grid,
            grid_size=settings.heatmap_grid_size,
        )
        self.analytics = AnalyticsComputer(
            high_threshold=settings.density_high_threshold,
            moderate_threshold=self.crowd_moderate,
            crowded_threshold=self.crowd_crowded,
            overcrowded_threshold=self.crowd_overcrowded,
        )

        # Shared, lock-protected state.
        self._lock = threading.Lock()
        self._overlay_jpeg: bytes | None = None
        self._raw_jpeg: bytes | None = None
        self._latest: dict | None = None
        self._latest_density_max: float = 0.0
        self._connected = False
        self._fps = 0.0
        self._last_frame_at: float | None = None

        self._thread: threading.Thread | None = None
        self._running = threading.Event()

    # --------------------------------------------------------------------- #
    # Lifecycle
    # --------------------------------------------------------------------- #
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._run, name=f"pipeline-{self.camera_id}", daemon=True
        )
        self._thread.start()
        logger.info("Camera '%s' pipeline started (source=%s)", self.camera_id, self.source)

    def stop(self) -> None:
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Camera '%s' pipeline stopped", self.camera_id)

    # --------------------------------------------------------------------- #
    # Processing loop
    # --------------------------------------------------------------------- #
    def _open_capture(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(_parse_source(self.source))
        # Keep latency low on RTSP by minimising the buffer.
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:  # pragma: no cover
            pass
        return cap

    def _run(self) -> None:
        cap = self._open_capture()
        min_period = 1.0 / max(1, self.settings.target_fps)
        ema_fps = 0.0
        reconnect_delay = 1.0

        while self._running.is_set():
            if not cap.isOpened():
                self._set_connected(False)
                logger.warning("Camera '%s' not opened; retrying…", self.camera_id)
                time.sleep(reconnect_delay)
                cap.release()
                cap = self._open_capture()
                reconnect_delay = min(reconnect_delay * 1.5, 10.0)
                continue

            t0 = time.time()
            ok, frame = cap.read()
            if not ok or frame is None:
                # End of a file loops; a dropped stream reconnects.
                self._set_connected(False)
                if isinstance(_parse_source(self.source), str) and self._is_file():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                logger.warning("Camera '%s' read failed; reconnecting…", self.camera_id)
                cap.release()
                time.sleep(reconnect_delay)
                cap = self._open_capture()
                continue

            reconnect_delay = 1.0
            self._set_connected(True)

            try:
                self._process_frame(frame)
            except Exception:  # noqa: BLE001 - never kill the loop
                logger.exception("Frame processing error on camera '%s'", self.camera_id)

            # Throttle to target FPS and update the EMA FPS estimate.
            elapsed = time.time() - t0
            if elapsed < min_period:
                time.sleep(min_period - elapsed)
            inst_fps = 1.0 / max(1e-6, time.time() - t0)
            ema_fps = inst_fps if ema_fps == 0 else 0.9 * ema_fps + 0.1 * inst_fps
            with self._lock:
                self._fps = round(ema_fps, 1)

        cap.release()

    def _is_file(self) -> bool:
        src = _parse_source(self.source)
        if isinstance(src, int):
            return False
        return not src.lower().startswith(("rtsp://", "http://", "https://", "rtmp://"))

    def _process_frame(self, frame: np.ndarray) -> None:
        frame = resize_keep(
            frame, self.settings.frame_width, self.settings.frame_height
        )

        detections = self.detector.track(frame)
        movements = self.movement.update(detections)
        density = self.density.estimate(frame.shape[:2], detections)
        result = self.analytics.compute(detections, density, movements)
        overlay = self.heatmap.render(frame, density)

        overlay_jpeg = encode_jpeg(overlay, self.settings.jpeg_quality)
        # A live raw preview is kept in memory only for the dashboard's
        # "original camera" pane. It is never persisted (store_raw_video guard
        # applies to disk/DB writes, handled in the storage layer).
        raw_jpeg = encode_jpeg(frame, self.settings.jpeg_quality)

        payload = {
            "camera_id": self.camera_id,
            "timestamp": result.timestamp,
            "people_count": result.people_count,
            "density_score": result.density_score,
            "average_density": result.average_density,
            "max_density": result.max_density,
            "crowd_level": result.crowd_level,
            "crowded_zones": result.crowded_zones,
            "movement_index": round(
                float(np.mean([m.speed for m in movements])) if movements else 0.0, 3
            ),
            "movements": [asdict(m) for m in movements],
        }

        with self._lock:
            self._overlay_jpeg = overlay_jpeg
            self._raw_jpeg = raw_jpeg
            self._latest = payload
            self._latest_density_max = result.max_density
            self._last_frame_at = result.timestamp

    # --------------------------------------------------------------------- #
    # Published state (thread-safe reads)
    # --------------------------------------------------------------------- #
    def _set_connected(self, value: bool) -> None:
        with self._lock:
            self._connected = value

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def snapshot_status(self) -> dict:
        with self._lock:
            return {
                "camera_id": self.camera_id,
                "running": self.running,
                "connected": self._connected,
                "fps": self._fps,
                "people_count": (self._latest or {}).get("people_count", 0),
                "last_frame_at": self._last_frame_at,
            }

    def latest_analytics(self) -> dict | None:
        with self._lock:
            return dict(self._latest) if self._latest else None

    def latest_overlay_jpeg(self) -> bytes | None:
        with self._lock:
            return self._overlay_jpeg

    def latest_raw_jpeg(self) -> bytes | None:
        with self._lock:
            return self._raw_jpeg

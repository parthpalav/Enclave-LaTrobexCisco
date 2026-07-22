"""Camera lifecycle manager.

A process-wide singleton that owns the running :class:`CameraPipeline`
instances and enforces the configured camera limit. The API layer talks to
this manager; it never touches pipelines directly.
"""

from __future__ import annotations

import threading

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.services.stream_service import CameraPipeline

logger = get_logger(__name__)


class CameraNotFound(Exception):
    pass


class CameraLimitReached(Exception):
    pass


class CameraManager:
    """Manages the set of active camera pipelines."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._pipelines: dict[str, CameraPipeline] = {}
        self._lock = threading.Lock()

    def add(
        self, camera_id: str, source: str, crowd_thresholds: dict | None = None
    ) -> CameraPipeline:
        with self._lock:
            if camera_id in self._pipelines:
                # Idempotent: restart if the same id is re-added.
                self._pipelines[camera_id].stop()
                del self._pipelines[camera_id]
            if len(self._pipelines) >= self.settings.max_cameras:
                raise CameraLimitReached(
                    f"Maximum of {self.settings.max_cameras} cameras reached"
                )
            pipeline = CameraPipeline(
                camera_id, source, self.settings, crowd_thresholds=crowd_thresholds
            )
            pipeline.start()
            self._pipelines[camera_id] = pipeline
            return pipeline

    def remove(self, camera_id: str) -> None:
        with self._lock:
            pipeline = self._pipelines.pop(camera_id, None)
        if pipeline is None:
            raise CameraNotFound(camera_id)
        pipeline.stop()

    def get(self, camera_id: str) -> CameraPipeline:
        pipeline = self._pipelines.get(camera_id)
        if pipeline is None:
            raise CameraNotFound(camera_id)
        return pipeline

    def get_optional(self, camera_id: str) -> CameraPipeline | None:
        return self._pipelines.get(camera_id)

    def list_ids(self) -> list[str]:
        return list(self._pipelines.keys())

    def statuses(self) -> list[dict]:
        return [p.snapshot_status() for p in self._pipelines.values()]

    @property
    def active_count(self) -> int:
        return len(self._pipelines)

    def shutdown(self) -> None:
        with self._lock:
            for pipeline in self._pipelines.values():
                pipeline.stop()
            self._pipelines.clear()


# Process-wide singleton (simple DI seam — overridable in tests).
_manager: CameraManager | None = None


def get_camera_manager() -> CameraManager:
    global _manager
    if _manager is None:
        _manager = CameraManager()
    return _manager

"""Movement analytics on top of ByteTrack IDs.

ByteTrack (run inside :class:`YoloDetector`) assigns stable IDs across frames.
This module consumes those IDs to derive per-person movement — velocity and
speed — which feeds the "people movement" analytic. It deliberately holds no
detection logic (single responsibility).
"""

from __future__ import annotations

import math

from app.models import Detection, TrackMovement


class MovementTracker:
    """Computes per-track velocity/speed between consecutive frames."""

    def __init__(self, max_missing_frames: int = 30):
        self.max_missing_frames = max_missing_frames
        # track_id -> (last_position, frames_since_seen)
        self._last_positions: dict[int, tuple[float, float]] = {}
        self._missing: dict[int, int] = {}

    def reset(self) -> None:
        self._last_positions.clear()
        self._missing.clear()

    def update(self, detections: list[Detection]) -> list[TrackMovement]:
        """Update internal state and return movement for currently seen tracks."""
        movements: list[TrackMovement] = []
        seen: set[int] = set()

        for det in detections:
            if det.track_id is None:
                continue
            tid = det.track_id
            seen.add(tid)
            pos = det.center
            prev = self._last_positions.get(tid)

            if prev is None:
                velocity = (0.0, 0.0)
                speed = 0.0
            else:
                vx, vy = pos[0] - prev[0], pos[1] - prev[1]
                velocity = (vx, vy)
                speed = math.hypot(vx, vy)

            movements.append(
                TrackMovement(
                    track_id=tid, position=pos, velocity=velocity, speed=speed
                )
            )
            self._last_positions[tid] = pos
            self._missing[tid] = 0

        # Age out tracks that disappeared.
        for tid in list(self._last_positions.keys()):
            if tid in seen:
                continue
            self._missing[tid] = self._missing.get(tid, 0) + 1
            if self._missing[tid] > self.max_missing_frames:
                self._last_positions.pop(tid, None)
                self._missing.pop(tid, None)

        return movements

    @property
    def active_tracks(self) -> int:
        return len(self._last_positions)

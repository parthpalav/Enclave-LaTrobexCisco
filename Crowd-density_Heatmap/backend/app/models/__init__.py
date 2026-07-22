"""AI pipeline components: detection, tracking, density and heatmap.

Also defines the shared value objects passed between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Detection:
    """A single detected (and optionally tracked) person in a frame."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    track_id: int | None = None

    @property
    def center(self) -> tuple[float, float]:
        """Centre of the bounding box."""
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def foot_point(self) -> tuple[float, float]:
        """Bottom-centre of the box — the person's ground contact point.

        Ground points give a more physically meaningful density map than
        box centres (heads far from the floor otherwise inflate density).
        """
        return ((self.x1 + self.x2) / 2.0, self.y2)

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


@dataclass(slots=True)
class TrackMovement:
    """Per-track movement between the previous and current frame."""

    track_id: int
    position: tuple[float, float]
    velocity: tuple[float, float] = (0.0, 0.0)
    speed: float = 0.0


@dataclass(slots=True)
class FrameResult:
    """Everything the pipeline produces for a single processed frame."""

    people_count: int
    density_score: float
    average_density: float
    max_density: float
    crowd_level: str = "low"
    crowded_zones: list[dict] = field(default_factory=list)
    movements: list[TrackMovement] = field(default_factory=list)
    detections: list[Detection] = field(default_factory=list)
    timestamp: float = 0.0


__all__ = ["Detection", "TrackMovement", "FrameResult"]

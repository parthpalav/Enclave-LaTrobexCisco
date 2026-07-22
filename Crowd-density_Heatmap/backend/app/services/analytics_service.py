"""Frame-level crowd analytics.

Turns a density field + detections + movements into the statistics required by
the spec: people count, density score, average/max density, crowded zones and a
movement index. Crowded zones are found by thresholding the smooth density map
and extracting blob centroids — no rectangular grid.
"""

from __future__ import annotations

import time

import cv2
import numpy as np

from app.models import Detection, FrameResult, TrackMovement


class AnalyticsComputer:
    """Pure computation of per-frame crowd statistics."""

    def __init__(
        self,
        high_threshold: float = 0.6,
        moderate_threshold: int = 5,
        crowded_threshold: int = 10,
        overcrowded_threshold: int = 20,
    ):
        self.high_threshold = high_threshold
        self.moderate_threshold = moderate_threshold
        self.crowded_threshold = crowded_threshold
        self.overcrowded_threshold = overcrowded_threshold

    def classify_crowd(self, people_count: int) -> str:
        """Map a head-count to a crowd level using the configured thresholds."""
        if people_count >= self.overcrowded_threshold:
            return "overcrowded"
        if people_count >= self.crowded_threshold:
            return "crowded"
        if people_count >= self.moderate_threshold:
            return "moderate"
        return "low"

    def crowded_zones(self, density: np.ndarray) -> list[dict]:
        """Extract crowded-zone blobs from the normalised density map.

        Returns a list of {x, y, radius, intensity} in frame pixel coordinates.
        """
        mask = (density >= self.high_threshold).astype(np.uint8) * 255
        if not mask.any():
            return []

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        zones: list[dict] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 4:  # ignore specks
                continue
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            m = np.zeros(density.shape, dtype=np.uint8)
            cv2.drawContours(m, [cnt], -1, 255, -1)
            intensity = float(density[m == 255].mean())
            zones.append(
                {
                    "x": round(float(x), 1),
                    "y": round(float(y), 1),
                    "radius": round(float(radius), 1),
                    "intensity": round(intensity, 3),
                }
            )
        zones.sort(key=lambda z: z["intensity"], reverse=True)
        return zones

    def compute(
        self,
        detections: list[Detection],
        density: np.ndarray,
        movements: list[TrackMovement],
    ) -> FrameResult:
        people_count = len(detections)
        if density.size:
            max_density = float(density.max())
            average_density = float(density.mean())
        else:
            max_density = average_density = 0.0

        # Density score: a single 0..100 crowd-pressure figure combining the
        # peak density with how many people are present.
        density_score = round(
            min(100.0, max_density * 100.0 * 0.7 + min(people_count, 100) * 0.3), 2
        )

        movement_index = (
            float(np.mean([m.speed for m in movements])) if movements else 0.0
        )

        return FrameResult(
            people_count=people_count,
            density_score=density_score,
            average_density=round(average_density, 4),
            max_density=round(max_density, 4),
            crowd_level=self.classify_crowd(people_count),
            crowded_zones=self.crowded_zones(density),
            movements=movements,
            detections=detections,
            timestamp=time.time(),
        )

"""Crowd density estimation via Gaussian Kernel Density Estimation.

Produces a smooth, continuous density field (no rectangular grids) from a set
of person coordinates. Computation happens at a downscaled resolution for speed
and the result is upsampled back to frame size.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from app.models import Detection
from app.models.gaussian import GaussianSplatter


class DensityEstimator:
    """Estimate a normalised crowd-density map from detections.

    Two interchangeable back-ends:
      * ``filter`` (default): stamp unit points then apply a separable Gaussian
        filter (SciPy). Fastest and the most numerically smooth.
      * ``kernel``: explicit additive Gaussian splatting via ``GaussianSplatter``
        — useful for testing and for exotic per-person weighting.
    """

    def __init__(
        self,
        sigma: float,
        kernel_size: int = 0,
        downscale: float = 0.5,
        method: str = "filter",
        source: str = "foot",
    ):
        self.sigma = sigma
        self.kernel_size = kernel_size
        self.downscale = max(0.05, min(1.0, downscale))
        self.method = method
        # Where each person deposits density: 'foot', 'center', or 'box'.
        self.source = source
        self._splatter = GaussianSplatter(sigma * self.downscale, kernel_size)
        # Running peak for temporally-stable normalisation (avoids flicker).
        self._running_max: float = 1e-6

    def reconfigure(self, sigma: float, kernel_size: int = 0) -> None:
        self.sigma = sigma
        self.kernel_size = kernel_size
        self._splatter.reconfigure(sigma * self.downscale, kernel_size)

    def estimate(
        self, frame_shape: tuple[int, int], detections: list[Detection]
    ) -> np.ndarray:
        """Return a full-resolution float density map in [0, 1].

        Args:
            frame_shape: (height, width) of the source frame.
            detections: detected people (foot points are used as anchors).
        """
        height, width = frame_shape
        dh = max(1, int(height * self.downscale))
        dw = max(1, int(width * self.downscale))
        sigma_ds = max(1.0, self.sigma * self.downscale)

        if not detections:
            self._running_max *= 0.9  # slowly decay so map re-scales when empty
            self._running_max = max(self._running_max, 1e-6)
            return np.zeros((height, width), dtype=np.float32)

        if self.source == "box":
            # Paint each person's whole detection area, then blur. This colours
            # the region a person occupies (their body) rather than a single dot,
            # and overlapping people accumulate into hotter zones.
            canvas = np.zeros((dh, dw), dtype=np.float32)
            for det in detections:
                x1 = max(0, min(dw - 1, int(det.x1 * self.downscale)))
                y1 = max(0, min(dh - 1, int(det.y1 * self.downscale)))
                x2 = max(0, min(dw, int(det.x2 * self.downscale)))
                y2 = max(0, min(dh, int(det.y2 * self.downscale)))
                if x2 > x1 and y2 > y1:
                    canvas[y1:y2, x1:x2] += 1.0
            density = gaussian_filter(canvas, sigma=sigma_ds, mode="constant")
        else:
            # Point modes: one anchor per person (ground point or box centre).
            points = []
            for det in detections:
                px, py = det.center if self.source == "center" else det.foot_point
                points.append((px * self.downscale, py * self.downscale))

            if self.method == "kernel":
                density = self._splatter.splat((dh, dw), points)
            else:
                canvas = np.zeros((dh, dw), dtype=np.float32)
                for px, py in points:
                    ix, iy = int(round(px)), int(round(py))
                    if 0 <= iy < dh and 0 <= ix < dw:
                        canvas[iy, ix] += 1.0
                density = gaussian_filter(canvas, sigma=sigma_ds, mode="constant")

        # Upsample smoothly to full resolution.
        density_full = cv2.resize(
            density, (width, height), interpolation=cv2.INTER_LINEAR
        )

        # Temporally stable normalisation.
        frame_peak = float(density_full.max())
        self._running_max = max(self._running_max * 0.95, frame_peak, 1e-6)
        normalized = np.clip(density_full / self._running_max, 0.0, 1.0)
        return normalized.astype(np.float32)

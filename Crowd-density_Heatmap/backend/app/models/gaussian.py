"""Gaussian kernel generation and additive splatting.

This module owns the *kernel* concern of the density pipeline so it can be
tuned/tested in isolation. Kernel size and sigma are configurable.
"""

from __future__ import annotations

import numpy as np

from app.utils.math import gaussian_kernel


class GaussianSplatter:
    """Accumulates 2D Gaussian kernels onto a density canvas.

    One kernel is stamped per person. Overlapping kernels add up, so busy
    regions accumulate high density while isolated people stay low — a true
    Gaussian kernel-density estimate, not a rectangular grid.
    """

    def __init__(self, sigma: float, kernel_size: int = 0):
        self.sigma = sigma
        self.kernel_size = kernel_size
        self._kernel = gaussian_kernel(sigma, kernel_size)

    def reconfigure(self, sigma: float, kernel_size: int = 0) -> None:
        if sigma != self.sigma or kernel_size != self.kernel_size:
            self.sigma = sigma
            self.kernel_size = kernel_size
            self._kernel = gaussian_kernel(sigma, kernel_size)

    @property
    def kernel(self) -> np.ndarray:
        return self._kernel

    def splat(
        self,
        shape: tuple[int, int],
        points: list[tuple[float, float]],
        weights: list[float] | None = None,
    ) -> np.ndarray:
        """Stamp a Gaussian kernel at each point onto an empty canvas.

        Args:
            shape: (height, width) of the output density map.
            points: list of (x, y) coordinates in canvas space.
            weights: optional per-point weights (defaults to 1.0).

        Returns:
            float32 density map of the requested shape.
        """
        height, width = shape
        canvas = np.zeros((height, width), dtype=np.float32)
        if not points:
            return canvas

        kernel = self._kernel
        k = kernel.shape[0]
        half = k // 2

        for idx, (x, y) in enumerate(points):
            cx, cy = int(round(x)), int(round(y))
            weight = 1.0 if weights is None else float(weights[idx])

            # Destination window (clipped to canvas bounds).
            x0, x1 = cx - half, cx + half + 1
            y0, y1 = cy - half, cy + half + 1
            dx0, dy0 = max(0, x0), max(0, y0)
            dx1, dy1 = min(width, x1), min(height, y1)
            if dx0 >= dx1 or dy0 >= dy1:
                continue

            # Matching window inside the kernel.
            kx0, ky0 = dx0 - x0, dy0 - y0
            kx1, ky1 = kx0 + (dx1 - dx0), ky0 + (dy1 - dy0)

            canvas[dy0:dy1, dx0:dx1] += weight * kernel[ky0:ky1, kx0:kx1]

        return canvas

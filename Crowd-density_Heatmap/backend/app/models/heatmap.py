"""Heatmap rendering: colour-map a density field and blend it over the frame.

The overlay is semi-transparent and fades smoothly to fully transparent in
sparse areas, so the original CCTV image stays visible where there are no
people — never rectangular blocks.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.utils.color import apply_colormap


class HeatmapGenerator:
    """Turns a normalised density map into a blended heatmap overlay."""

    def __init__(
        self,
        alpha: float = 0.5,
        min_density: float = 0.05,
        colormap: str = "crowdvision",
        base_alpha: float = 0.0,
        mode: str = "overlay",
        grid: bool = False,
        grid_size: int = 32,
    ):
        self.alpha = alpha
        self.min_density = min_density
        self.colormap = colormap
        # Baseline opacity applied everywhere (blue wash). 0 → sparse areas stay
        # transparent; >0 → full-frame heatmap like classic CCTV overlays.
        self.base_alpha = base_alpha
        # 'overlay' = blend over the camera; 'pure' = standalone abstract heatmap.
        self.mode = mode
        self.grid = grid
        self.grid_size = max(4, grid_size)

    # Neutral grey used for empty ("no crowd") regions in pure mode.
    _GREY = (105, 105, 105)

    def colorize(self, density: np.ndarray) -> np.ndarray:
        """Return a BGR colour image of the density map (no blending)."""
        d8 = np.clip(density * 255.0, 0, 255).astype(np.uint8)
        return apply_colormap(d8, self.colormap)

    def render(self, frame: np.ndarray, density: np.ndarray) -> np.ndarray:
        """Overlay the heatmap on ``frame`` using per-pixel alpha blending.

        Args:
            frame: BGR source frame (HxWx3 uint8).
            density: normalised density in [0, 1], same HxW as the frame.

        Returns:
            BGR frame with the heatmap blended in.
        """
        if density.shape[:2] != frame.shape[:2]:
            density = cv2.resize(
                density, (frame.shape[1], frame.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )

        if self.mode == "pure":
            return self._render_pure(density)

        colored = self.colorize(density)

        # Per-pixel alpha ramps from `base_alpha` (sparse/empty → blue wash) up to
        # `alpha` at peak density (dense → opaque red). With base_alpha > 0 the
        # whole frame is tinted blue and warms smoothly where crowds form — the
        # classic CCTV heatmap look. With base_alpha = 0 empty areas stay clear.
        alpha_mask = self.base_alpha + (self.alpha - self.base_alpha) * density
        alpha_mask = np.clip(alpha_mask, 0.0, 1.0)[..., None].astype(np.float32)

        blended = frame.astype(np.float32) * (1.0 - alpha_mask) + colored.astype(
            np.float32
        ) * alpha_mask
        return blended.astype(np.uint8)

    def _render_pure(self, density: np.ndarray) -> np.ndarray:
        """Standalone abstract heatmap — no camera image, no faces.

        Empty ("no crowd") regions are neutral grey; density then ramps
        blue → green → yellow → red. Nothing of the original scene is visible;
        only colour intensity conveys crowd density.
        """
        h, w = density.shape[:2]
        colored = self.colorize(density).astype(np.float32)
        grey = np.empty((h, w, 3), np.float32)
        grey[:] = self._GREY

        # Blend grey → colour over [0, cutoff] so empty stays grey and any real
        # density shows colour with a soft edge (no hard blocks).
        cutoff = max(self.min_density, 0.04)
        t = np.clip(density / cutoff, 0.0, 1.0)[..., None]
        out = grey * (1.0 - t) + colored * t
        out = out.astype(np.uint8)

        if self.grid:
            self._draw_grid(out)
        return out

    def _draw_grid(self, img: np.ndarray) -> None:
        """Draw a faint reference grid in-place (classic CCTV-heatmap look)."""
        h, w = img.shape[:2]
        line = (60, 60, 60)
        for x in range(0, w, self.grid_size):
            cv2.line(img, (x, 0), (x, h), line, 1)
        for y in range(0, h, self.grid_size):
            cv2.line(img, (0, y), (w, y), line, 1)

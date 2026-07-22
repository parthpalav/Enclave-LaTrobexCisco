"""Colour-map utilities.

Provides the CrowdVision colour ramp (blue → green → yellow → orange → red)
as a 256-entry BGR lookup table for fast per-frame application, plus a helper
to fetch an OpenCV built-in colormap by name.
"""

from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

# Control points along the ramp: (position 0..1, (R, G, B)).
_CROWDVISION_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.00, (0, 0, 128)),      # deep blue  — sparse
    (0.25, (0, 128, 255)),    # cyan/blue
    (0.45, (0, 200, 0)),      # green
    (0.65, (255, 255, 0)),    # yellow
    (0.82, (255, 140, 0)),    # orange
    (1.00, (200, 0, 0)),      # red        — dense
]


@lru_cache(maxsize=1)
def crowdvision_lut() -> np.ndarray:
    """Return a (256, 1, 3) uint8 BGR LUT for the CrowdVision ramp."""
    positions = np.array([s[0] for s in _CROWDVISION_STOPS])
    colors = np.array([s[1] for s in _CROWDVISION_STOPS], dtype=np.float32)  # RGB

    x = np.linspace(0.0, 1.0, 256)
    r = np.interp(x, positions, colors[:, 0])
    g = np.interp(x, positions, colors[:, 1])
    b = np.interp(x, positions, colors[:, 2])

    # OpenCV uses BGR ordering.
    lut = np.stack([b, g, r], axis=-1).astype(np.uint8)
    return lut.reshape(256, 1, 3)


_OPENCV_COLORMAPS = {
    "jet": cv2.COLORMAP_JET,
    "turbo": cv2.COLORMAP_TURBO,
    "hot": cv2.COLORMAP_HOT,
    "inferno": cv2.COLORMAP_INFERNO,
    "viridis": cv2.COLORMAP_VIRIDIS,
}


def apply_colormap(normalized: np.ndarray, colormap: str = "crowdvision") -> np.ndarray:
    """Map a uint8 single-channel image to a BGR colour image.

    Args:
        normalized: HxW uint8 array (0..255).
        colormap: 'crowdvision' or an OpenCV colormap name.

    Returns:
        HxWx3 uint8 BGR image.
    """
    key = colormap.lower()
    if key in ("crowdvision", "crowd", "default"):
        return cv2.applyColorMap(normalized, crowdvision_lut())
    if key in _OPENCV_COLORMAPS:
        return cv2.applyColorMap(normalized, _OPENCV_COLORMAPS[key])
    # Unknown name → fall back to the project ramp.
    return cv2.applyColorMap(normalized, crowdvision_lut())

"""Small math helpers for density estimation."""

from __future__ import annotations

import numpy as np


def gaussian_kernel(sigma: float, kernel_size: int = 0) -> np.ndarray:
    """Return a normalised 2D Gaussian kernel.

    Args:
        sigma: Standard deviation in pixels.
        kernel_size: Odd kernel side length. If 0, derived as 6*sigma+1.

    Returns:
        (k, k) float32 kernel summing to 1.
    """
    sigma = max(float(sigma), 1e-3)
    if kernel_size <= 0:
        kernel_size = int(6 * sigma + 1)
    if kernel_size % 2 == 0:
        kernel_size += 1

    ax = np.arange(-(kernel_size // 2), kernel_size // 2 + 1, dtype=np.float32)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2.0 * sigma**2))
    total = kernel.sum()
    if total > 0:
        kernel /= total
    return kernel.astype(np.float32)


def normalize01(array: np.ndarray, ref_max: float | None = None) -> np.ndarray:
    """Normalise an array into [0, 1].

    Args:
        array: Input float array.
        ref_max: Optional fixed maximum for temporally stable scaling. If None,
            the array's own max is used.
    """
    arr = array.astype(np.float32)
    max_val = ref_max if ref_max is not None else float(arr.max())
    if max_val <= 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip(arr / max_val, 0.0, 1.0)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

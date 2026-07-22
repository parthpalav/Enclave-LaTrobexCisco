"""Heatmap, density and Gaussian generation tests (no GPU/model needed)."""

from __future__ import annotations

import numpy as np

from app.models import Detection
from app.models.density import DensityEstimator
from app.models.gaussian import GaussianSplatter
from app.models.heatmap import HeatmapGenerator
from app.utils.color import apply_colormap, crowdvision_lut
from app.utils.math import gaussian_kernel


def test_gaussian_kernel_is_normalised_and_odd():
    k = gaussian_kernel(sigma=4.0)
    assert k.shape[0] == k.shape[1]
    assert k.shape[0] % 2 == 1
    assert abs(k.sum() - 1.0) < 1e-5
    # Peak is at the centre.
    c = k.shape[0] // 2
    assert k[c, c] == k.max()


def test_kernel_size_override():
    k = gaussian_kernel(sigma=3.0, kernel_size=11)
    assert k.shape == (11, 11)


def test_splatter_accumulates_overlapping_kernels():
    splat = GaussianSplatter(sigma=5.0)
    single = splat.splat((100, 100), [(50, 50)])
    doubled = splat.splat((100, 100), [(50, 50), (50, 50)])
    assert doubled[50, 50] > single[50, 50]


def test_density_is_smooth_and_normalised(sample_detections):
    est = DensityEstimator(sigma=25.0, downscale=0.5)
    density = est.estimate((720, 1280), sample_detections)
    assert density.shape == (720, 1280)
    assert density.min() >= 0.0
    assert density.max() <= 1.0
    # The dense cluster region should be hotter than the loner.
    cluster = density[300:410, 600:660].max()
    loner = density[100:200, 100:140].max()
    assert cluster > loner


def test_empty_detections_give_zero_density():
    est = DensityEstimator(sigma=25.0)
    density = est.estimate((360, 640), [])
    assert density.max() == 0.0


def test_colormap_lut_shape_and_endpoints():
    lut = crowdvision_lut()
    assert lut.shape == (256, 1, 3)
    # Low end is bluish (B > R), high end is reddish (R > B).
    low_b, _, low_r = lut[0, 0]
    high_b, _, high_r = lut[255, 0]
    assert low_b > low_r
    assert high_r > high_b


def test_heatmap_overlay_keeps_shape_and_blends(blank_frame, sample_detections):
    est = DensityEstimator(sigma=25.0)
    gen = HeatmapGenerator(alpha=0.5, min_density=0.05)
    density = est.estimate(blank_frame.shape[:2], sample_detections)
    overlay = gen.render(blank_frame, density)
    assert overlay.shape == blank_frame.shape
    assert overlay.dtype == np.uint8
    # Overlay must have added colour somewhere (frame was all black).
    assert overlay.sum() > 0


def test_transparent_where_no_people():
    frame = np.full((360, 640, 3), 128, dtype=np.uint8)
    gen = HeatmapGenerator(alpha=0.6, min_density=0.05)
    density = np.zeros((360, 640), dtype=np.float32)
    overlay = gen.render(frame, density)
    # With zero density the original frame must be unchanged.
    assert np.array_equal(overlay, frame)


def test_apply_colormap_unknown_falls_back():
    img = np.linspace(0, 255, 256, dtype=np.uint8).reshape(16, 16)
    out = apply_colormap(img, "does-not-exist")
    assert out.shape == (16, 16, 3)

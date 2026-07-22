"""Shared pytest fixtures."""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def blank_frame() -> np.ndarray:
    """A 720p black BGR frame."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def sample_detections():
    from app.models import Detection

    # Two clusters of people plus one loner.
    return [
        Detection(600, 300, 640, 400, 0.9, track_id=1),
        Detection(620, 310, 660, 410, 0.8, track_id=2),
        Detection(610, 305, 650, 405, 0.85, track_id=3),
        Detection(100, 100, 140, 200, 0.7, track_id=4),
    ]

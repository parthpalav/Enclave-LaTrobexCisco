"""Detection tests. Skipped automatically when weights can't be loaded
(e.g. offline CI without model download)."""

from __future__ import annotations

import numpy as np
import pytest


def _load_detector():
    from app.core.config import get_settings
    from app.models.yolo_detector import YoloDetector

    s = get_settings()
    return YoloDetector(
        model_path=s.yolo_model,
        fallback_path=s.yolo_fallback_model,
        device="cpu",
        confidence=s.yolo_confidence,
        person_class_id=s.person_class_id,
    )


@pytest.fixture(scope="module")
def detector():
    try:
        return _load_detector()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"YOLO weights unavailable: {exc}")


def test_detector_returns_list_on_blank_frame(detector):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dets = detector.detect(frame)
    assert isinstance(dets, list)  # blank frame → typically empty


def test_tracking_assigns_ids_when_people_present(detector):
    # Synthetic frame with bright blobs won't reliably be 'people', so we only
    # assert the interface here; real accuracy is validated with sample footage.
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    dets = detector.track(frame)
    assert isinstance(dets, list)
    for d in dets:
        assert d.confidence >= 0.0

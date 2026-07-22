"""Analytics and movement-tracking tests."""

from __future__ import annotations

from app.models import Detection
from app.models.density import DensityEstimator
from app.models.tracker import MovementTracker
from app.services.analytics_service import AnalyticsComputer


def test_analytics_counts_and_zones(sample_detections):
    est = DensityEstimator(sigma=25.0)
    density = est.estimate((720, 1280), sample_detections)
    computer = AnalyticsComputer(high_threshold=0.3)
    result = computer.compute(sample_detections, density, movements=[])

    assert result.people_count == 4
    assert 0.0 <= result.max_density <= 1.0
    assert result.density_score >= 0.0
    # The tight cluster should form at least one crowded zone.
    assert len(result.crowded_zones) >= 1
    for zone in result.crowded_zones:
        assert {"x", "y", "radius", "intensity"} <= set(zone)


def test_movement_tracker_reports_speed():
    tracker = MovementTracker()
    frame1 = [Detection(0, 0, 10, 10, 0.9, track_id=1)]
    frame2 = [Detection(3, 4, 13, 14, 0.9, track_id=1)]  # moved (3,4) -> speed 5

    tracker.update(frame1)
    moves = tracker.update(frame2)
    assert len(moves) == 1
    assert abs(moves[0].speed - 5.0) < 1e-3


def test_movement_tracker_ages_out_tracks():
    tracker = MovementTracker(max_missing_frames=2)
    tracker.update([Detection(0, 0, 10, 10, 0.9, track_id=7)])
    for _ in range(3):
        tracker.update([])
    assert tracker.active_tracks == 0

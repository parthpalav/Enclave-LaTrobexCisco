"""Persistent camera-to-floor homography projection."""

import json
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "camera_calibrations.json",
)


class HomographyCalibrator:
    """Loads and applies per-camera image-to-floor transforms."""

    def __init__(self, filepath: str = CALIBRATION_FILE):
        self.filepath = filepath
        self.calibrations: Dict[str, Dict] = {}
        self.matrices: Dict[str, np.ndarray] = {}
        self.load_calibrations()

    def load_calibrations(self) -> None:
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as handle:
                self.calibrations = json.load(handle)
            self.recompute_all_matrices()
        except (OSError, ValueError, TypeError) as exc:
            print(f"[Homography] Warning: failed to load calibrations: {exc}")
            self.calibrations = {}
            self.matrices = {}

    def recompute_all_matrices(self) -> None:
        self.matrices.clear()
        for camera_id, data in self.calibrations.items():
            src = np.asarray(data.get("src_points", []), dtype=np.float32)
            dst = np.asarray(data.get("dst_points", []), dtype=np.float32)
            if src.shape == (4, 2) and dst.shape == (4, 2):
                matrix, _ = cv2.findHomography(src, dst)
                if matrix is not None:
                    self.matrices[camera_id] = matrix

    def save_to_disk(self) -> None:
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        try:
            with open(self.filepath, "w", encoding="utf-8") as handle:
                json.dump(self.calibrations, handle, indent=2)
        except OSError as exc:
            print(f"[Homography] Warning: failed to save calibrations: {exc}")

    def set_calibration(
        self,
        camera_id: str,
        src_points: List[List[float]],
        dst_points: List[List[float]],
    ) -> bool:
        src = np.asarray(src_points, dtype=np.float32)
        dst = np.asarray(dst_points, dtype=np.float32)
        if src.shape != (4, 2) or dst.shape != (4, 2):
            return False
        matrix, _ = cv2.findHomography(src, dst)
        if matrix is None:
            return False
        self.calibrations[camera_id] = {
            "src_points": src_points,
            "dst_points": dst_points,
        }
        self.matrices[camera_id] = matrix
        self.save_to_disk()
        return True

    def get_matrix(self, camera_id: str) -> Optional[np.ndarray]:
        return self.matrices.get(camera_id)

    def is_calibrated(self, camera_id: str) -> bool:
        return camera_id in self.matrices

    def transform_point(self, camera_id: str, x: float, y: float) -> Optional[Tuple[float, float]]:
        matrix = self.matrices.get(camera_id)
        if matrix is None:
            return None
        point = np.asarray([[[x, y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(point, matrix)[0, 0]
        return round(float(projected[0]), 5), round(float(projected[1]), 5)

    def transform_velocity(
        self,
        camera_id: str,
        x: float,
        y: float,
        vx: float,
        vy: float,
    ) -> Optional[Tuple[float, float]]:
        start = self.transform_point(camera_id, x, y)
        end = self.transform_point(camera_id, x + vx, y + vy)
        if start is None or end is None:
            return None
        return round(end[0] - start[0], 5), round(end[1] - start[1], 5)


calibrator = HomographyCalibrator()

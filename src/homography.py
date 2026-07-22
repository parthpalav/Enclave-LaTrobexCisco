"""
Homography Calibration & Perspective Projection Module
========================================================
Maps 2D camera image coordinates (pixels) to continuous real-world
2D ground floor plan coordinates using 4-point Perspective Homography (H).
"""

import os
import json
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional

CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "camera_calibrations.json"
)

class HomographyCalibrator:
    """
    Manages camera-to-floor homography transformation matrices.
    """
    def __init__(self, filepath: str = CALIBRATION_FILE):
        self.filepath = filepath
        self.calibrations: Dict[str, Dict] = {}
        self.matrices: Dict[str, np.ndarray] = {}
        self.load_calibrations()

    def load_calibrations(self):
        """Loads persistent 4-point calibration data from JSON."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    self.calibrations = json.load(f)
                self.recompute_all_matrices()
            except Exception as e:
                print(f"[Homography] Warning: Failed to load calibrations: {e}")
                self.calibrations = {}

    def save_to_disk(self):
        """Saves calibration dictionary to disk."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.calibrations, f, indent=2)
        except Exception as e:
            print(f"[Homography] Error saving calibrations to disk: {e}")

    def recompute_all_matrices(self):
        """Recomputes OpenCV H matrices for all saved calibrations."""
        self.matrices.clear()
        for cam_id, data in self.calibrations.items():
            src_pts = np.array(data.get("src_points", []), dtype=np.float32)
            dst_pts = np.array(data.get("dst_points", []), dtype=np.float32)
            if len(src_pts) == 4 and len(dst_pts) == 4:
                H, _ = cv2.findHomography(src_pts, dst_pts)
                if H is not None:
                    self.matrices[cam_id] = H

    def set_calibration(self, camera_id: str, src_points: List[List[float]], dst_points: List[List[float]]) -> bool:
        """
        Sets 4-point calibration for a camera.
        src_points: 4 points in image pixel space [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
        dst_points: 4 points in ground floor space [[X0,Y0], [X1,Y1], [X2,Y2], [X3,Y3]] (0.0 - 1.0)
        """
        if len(src_points) != 4 or len(dst_points) != 4:
            return False

        src_arr = np.array(src_points, dtype=np.float32)
        dst_arr = np.array(dst_points, dtype=np.float32)

        H, _ = cv2.findHomography(src_arr, dst_arr)
        if H is None:
            return False

        self.calibrations[camera_id] = {
            "src_points": src_points,
            "dst_points": dst_points
        }
        self.matrices[camera_id] = H
        self.save_to_disk()
        print(f"[Homography] Calibration saved for camera '{camera_id}'.")
        return True

    def get_matrix(self, camera_id: str) -> Optional[np.ndarray]:
        """Returns the 3x3 Homography matrix H for a camera, or None if uncalibrated."""
        return self.matrices.get(camera_id)

    def is_calibrated(self, camera_id: str) -> bool:
        """Returns True if the camera has an active Homography calibration matrix."""
        return camera_id in self.matrices

    def transform_point(self, camera_id: str, x: float, y: float) -> Optional[Tuple[float, float]]:
        """
        Transforms a pixel point (x, y) into ground floor coordinates (X, Y) [0.0 - 1.0].
        Returns (X, Y) or None if camera is not calibrated.
        """
        H = self.matrices.get(camera_id)
        if H is None:
            return None

        pt = np.array([[[x, y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, H)
        tx, ty = float(transformed[0][0][0]), float(transformed[0][0][1])
        return round(tx, 4), round(ty, 4)

    def transform_velocity(self, camera_id: str, x: float, y: float, vx: float, vy: float) -> Optional[Tuple[float, float]]:
        """
        Transforms a 2D image velocity vector (vx, vy) at point (x, y) into ground velocity vector (VX, VY).
        """
        H = self.matrices.get(camera_id)
        if H is None:
            return None

        p1 = self.transform_point(camera_id, x, y)
        p2 = self.transform_point(camera_id, x + vx, y + vy)
        if p1 is None or p2 is None:
            return None

        return round(p2[0] - p1[0], 4), round(p2[1] - p1[1], 4)

# Global calibrator instance
calibrator = HomographyCalibrator()

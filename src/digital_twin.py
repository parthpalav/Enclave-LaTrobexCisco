import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from homography import calibrator

class DigitalTwinEngine:
    """
    Digital Twin Simulation & Spatial Radar Engine.
    Maps 2D camera perception into a top-down virtual floor plane (Digital Twin),
    rendering real-time digital avatar nodes, velocity trajectories, risk zones,
    and projected future positions (30s, 60s, 120s horizons).
    """
    def __init__(self, twin_width: int = 320, twin_height: int = 320, grid_rows: int = 20, grid_cols: int = 20):
        self.twin_width = twin_width
        self.twin_height = twin_height
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

    def render_overhead_map(
        self,
        tracks: List[Dict[str, Any]],
        track_velocities: Dict[int, Tuple[float, float]],
        divergence_map: np.ndarray,
        predicted_risk: Dict[str, float],
        frame_shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Renders top-down 2D Digital Twin Radar View.
        """
        H_cam, W_cam = frame_shape
        canvas = np.full((self.twin_height, self.twin_width, 3), (25, 25, 30), dtype=np.uint8)

        # Draw floor grid lines
        grid_step = self.twin_width // 10
        for x in range(0, self.twin_width, grid_step):
            cv2.line(canvas, (x, 0), (x, self.twin_height), (45, 45, 55), 1)
        for y in range(0, self.twin_height, grid_step):
            cv2.line(canvas, (0, y), (self.twin_width, y), (45, 45, 55), 1)

        # Title
        cv2.putText(canvas, "DIGITAL TWIN (Overhead Space)", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # Render Divergence Heatmap Risk Zones on Digital Twin Space
        conv_map = np.maximum(0.0, -divergence_map)
        if np.max(conv_map) > 0.02:
            norm_conv = (conv_map / (np.max(conv_map) + 1e-5) * 255).astype(np.uint8)
            heat_twin = cv2.applyColorMap(cv2.resize(norm_conv, (self.twin_width, self.twin_height)), cv2.COLORMAP_JET)
            canvas = cv2.addWeighted(canvas, 0.75, heat_twin, 0.25, 0)

        # Map tracked persons into Digital Twin Overhead Coordinates
        for t in tracks:
            tid = t["track_id"]
            cx, cy = t["center_xy"]

            # Map camera (X, Y) -> top-down digital twin plane (X_twin, Z_twin)
            # Normalization assuming perspective ground mapping
            tx = int(min(max((cx / W_cam) * self.twin_width, 10), self.twin_width - 10))
            tz = int(min(max((cy / H_cam) * self.twin_height, 10), self.twin_height - 10))

            # Fetch velocity for predictive trajectory projection
            vx, vy = track_velocities.get(tid, (0.0, 0.0))

            # Avatar color tied to track ID
            color_hue = (tid * 47) % 180
            avatar_color = cv2.cvtColor(np.uint8([[[color_hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
            avatar_color = (int(avatar_color[0]), int(avatar_color[1]), int(avatar_color[2]))

            # Draw digital avatar node (outer ring + center core)
            cv2.circle(canvas, (tx, tz), 8, avatar_color, 2, cv2.LINE_AA)
            cv2.circle(canvas, (tx, tz), 4, (0, 255, 0), -1, cv2.LINE_AA)

            # Draw predictive trajectory vector (+500ms lookahead on digital twin plane)
            speed = np.hypot(vx, vy)
            if speed > 0.3:
                pred_tx = int(tx + vx * 4.0)
                pred_tz = int(tz + vy * 4.0)
                pred_tx = int(min(max(pred_tx, 5), self.twin_width - 5))
                pred_tz = int(min(max(pred_tz, 5), self.twin_height - 5))

                cv2.arrowedLine(canvas, (tx, tz), (pred_tx, pred_tz), (0, 255, 255), 2, cv2.LINE_AA, 0, 0.3)
                cv2.circle(canvas, (pred_tx, pred_tz), 3, (255, 255, 0), -1, cv2.LINE_AA)

            # ID label
            cv2.putText(canvas, f"ID:{tid}", (tx + 10, tz + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        # Outer border
        cv2.rectangle(canvas, (0, 0), (self.twin_width - 1, self.twin_height - 1), (0, 255, 255), 1)

        return canvas

    def get_digital_twin_state(self, tracks: List[Dict[str, Any]], track_velocities: Dict[int, Tuple[float, float]], frame_shape: Tuple[int, int], camera_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Exports structured digital twin state payload (for simulation/web API/dashboard).
        If camera_id has a 4-point homography calibration, uses true perspective ground projection.
        """
        H_cam, W_cam = frame_shape
        avatars = []
        is_homography_active = False

        if camera_id and calibrator.is_calibrated(camera_id):
            is_homography_active = True

        for t in tracks:
            tid = t["track_id"]
            cx, cy = t["center_xy"]
            bbox = t.get("bbox", [0, 0, 0, 0])
            # Feet position (bottom center of bounding box) is physically on the ground plane
            feet_x = cx
            feet_y = bbox[1] + bbox[3] if len(bbox) == 4 else cy

            vx, vy = track_velocities.get(tid, (0.0, 0.0))

            if is_homography_active and camera_id:
                ground_pt = calibrator.transform_point(camera_id, feet_x, feet_y)
                ground_vel = calibrator.transform_velocity(camera_id, feet_x, feet_y, vx, vy)
                if ground_pt is not None:
                    # Ground coords in percentage [0-100]
                    tx = round(ground_pt[0] * 100.0, 2)
                    tz = round(ground_pt[1] * 100.0, 2)
                    if ground_vel is not None:
                        vx, vy = ground_vel[0] * 100.0, ground_vel[1] * 100.0
                else:
                    tx = round((cx / W_cam) * 100.0, 2)
                    tz = round((cy / H_cam) * 100.0, 2)
            else:
                tx = round((cx / W_cam) * 100.0, 2)
                tz = round((cy / H_cam) * 100.0, 2)

            avatars.append({
                "avatar_id": tid,
                "position_twin_xz": [tx, tz],
                "velocity_vector": [round(vx, 2), round(vy, 2)],
                "predicted_position_500ms": [round(tx + vx * 0.5, 2), round(tz + vy * 0.5, 2)],
                "calibrated_homography": is_homography_active
            })

        return {
            "entity": "CrowdDigitalTwinSpace",
            "active_avatars_count": len(avatars),
            "avatars": avatars,
            "homography_calibrated": is_homography_active
        }

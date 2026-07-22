import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from homography import calibrator

class DigitalTwinEngine:
    """
    Digital Twin Simulation & Spatial Radar Engine.
    Maps 2D camera perception into a top-down virtual floor plane (Digital Twin),
    rendering real-time digital avatar nodes, velocity trajectories,
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
        frame_shape: Tuple[int, int],
        camera_id: str = ""
    ) -> np.ndarray:
        """
        Renders top-down 2D Digital Twin Radar View.
        """
        H_cam, W_cam = frame_shape
        canvas = np.full((self.twin_height, self.twin_width, 3), (8, 12, 20), dtype=np.uint8)

        # Map tracked persons into Digital Twin Overhead Coordinates
        for t in tracks:
            tid = t["track_id"]
            cx, cy = t["center_xy"]

            tx = int(min(max((cx / W_cam) * self.twin_width, 10), self.twin_width - 10))
            tz = int(min(max((cy / H_cam) * self.twin_height, 10), self.twin_height - 10))

            # Match the camera overlay arrow direction in the mini-map.
            vx, vy = track_velocities.get(tid, (0.0, 0.0))
            vx = (vx / W_cam) * self.twin_width
            vy = (vy / H_cam) * self.twin_height

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

        return canvas

    def get_digital_twin_state(
        self,
        tracks: List[Dict[str, Any]],
        track_velocities: Dict[int, Tuple[float, float]],
        frame_shape: Tuple[int, int],
        camera_id: str = "",
    ) -> Dict[str, Any]:
        """
        Exports structured digital twin state payload (for simulation/web API/dashboard).
        """
        H_cam, W_cam = frame_shape
        avatars = []
        for t in tracks:
            tid = t["track_id"]
            cx, cy = t["center_xy"]
            vx, vy = track_velocities.get(tid, (0.0, 0.0))
            screen_vx = (vx / W_cam) * 100.0
            screen_vy = (vy / H_cam) * 100.0
            bbox = t.get("bbox", [cx, cy, 0, 0])
            feet_x = cx
            feet_y = float(bbox[1] + bbox[3]) if len(bbox) == 4 else cy
            projected = calibrator.transform_point(camera_id, feet_x, feet_y) if camera_id else None
            projected_velocity = calibrator.transform_velocity(camera_id, feet_x, feet_y, vx, vy) if camera_id else None
            floor_vx, floor_vy = screen_vx, screen_vy
            tx = round((cx / W_cam) * 100.0, 2)
            tz = round((cy / H_cam) * 100.0, 2)
            floor_position = [tx, tz]
            if projected is not None:
                floor_position = [round(projected[0] * 100.0, 2), round(projected[1] * 100.0, 2)]
                if projected_velocity is not None:
                    floor_vx, floor_vy = projected_velocity[0] * 100.0, projected_velocity[1] * 100.0

            avatars.append({
                "avatar_id": tid,
                "position_twin_xz": [tx, tz],
                "floor_position_twin_xz": floor_position,
                "velocity_vector": [round(screen_vx, 2), round(screen_vy, 2)],
                "floor_velocity_vector": [round(floor_vx, 2), round(floor_vy, 2)],
                "predicted_position_500ms": [round(tx + screen_vx * 0.5, 2), round(tz + screen_vy * 0.5, 2)],
                "homography_calibrated": projected is not None,
                "calibrated_homography": projected is not None,
            })

        return {
            "entity": "CrowdDigitalTwinSpace",
            "active_avatars_count": len(avatars),
            "homography_calibrated": bool(camera_id and calibrator.is_calibrated(camera_id)),
            "avatars": avatars
        }

import time
import numpy as np
from typing import Dict, Any, Tuple, Optional
from config import PipelineConfig
from detect_track import PersonTracker
from optical_flow import create_optical_flow_backend
from risk_signals import RiskEvaluator
from prediction import CrowdAdvectionPredictor
from digital_twin import DigitalTwinEngine
from visualize import DebugVisualizer

class CrowdFlowPipeline:
    """
    Complete end-to-end Crowd Detection, Tracking, Optical Flow, Divergence Risk,
    Advection-based Prediction, and Digital Twin Engine Pipeline.
    """
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.device = config.device

        print(f"[Pipeline] Initializing pipeline on {self.device}...")
        self.tracker = PersonTracker(config.detection, device=self.device)
        self.flow_backend = create_optical_flow_backend(config.optical_flow, device=self.device)
        
        grid_rows = config.optical_flow.grid_rows
        grid_cols = config.optical_flow.grid_cols
        
        self.risk_evaluator = RiskEvaluator(config.risk, grid_rows=grid_rows, grid_cols=grid_cols)
        self.predictor = CrowdAdvectionPredictor(config.prediction, config.risk, grid_rows=grid_rows, grid_cols=grid_cols)
        self.digital_twin = DigitalTwinEngine(grid_rows=grid_rows, grid_cols=grid_cols)
        self.visualizer = DebugVisualizer(config.visualization, grid_rows=grid_rows, grid_cols=grid_cols)

        self.prev_frame: Optional[np.ndarray] = None
        self.smoothed_flow: Optional[np.ndarray] = None
        self.frame_idx = 0
        self.fps_history = []
        self.last_timestamp = time.time()

    def process_frame(self, frame: np.ndarray, camera_id: Optional[str] = None) -> Tuple[Dict[str, Any], np.ndarray]:
        """
        Process single frame (BGR image array).
        Returns:
            contract_output: Structured JSON-serializable dict matching output contract
            rendered_frame: Visual overlay image canvas
        """
        self.frame_idx += 1
        curr_time = time.time()
        delta_time = curr_time - self.last_timestamp
        self.last_timestamp = curr_time
        instant_fps = 1.0 / max(delta_time, 1e-4)

        self.fps_history.append(instant_fps)
        if len(self.fps_history) > 30:
            self.fps_history.pop(0)
        avg_fps = float(np.mean(self.fps_history))

        timings: Dict[str, float] = {}

        # 1. Detection & Tracking Stage
        tracks, headcount, t_detect = self.tracker.process_frame(frame)
        timings["detect_track_ms"] = round(t_detect, 2)

        # 2. Dense Optical Flow Stage
        if self.prev_frame is None:
            self.prev_frame = frame.copy()
            grid_r = self.config.optical_flow.grid_rows
            grid_c = self.config.optical_flow.grid_cols
            dense_flow = np.zeros((self.config.optical_flow.downsample_height, self.config.optical_flow.downsample_width, 2), dtype=np.float32)
            binned_flow = np.zeros((grid_r, grid_c, 2), dtype=np.float32)
            self.smoothed_flow = binned_flow.copy()
            t_flow = 0.0
        else:
            dense_flow, raw_binned, t_flow = self.flow_backend.compute(self.prev_frame, frame)
            self.prev_frame = frame.copy()
            
            if self.smoothed_flow is None:
                self.smoothed_flow = raw_binned
            else:
                self.smoothed_flow = 0.65 * raw_binned + 0.35 * self.smoothed_flow
            binned_flow = self.smoothed_flow
        
        timings["flow_ms"] = round(t_flow, 2)

        # 3. Divergence & Risk Stage
        t_risk_start = time.perf_counter()
        H, W, _ = frame.shape
        density_map = self.risk_evaluator.compute_density_map(tracks, (H, W), binned_flow=binned_flow)
        risk_score_current, divergence_map, counterflow_map, cell_risk_map = self.risk_evaluator.evaluate_risk(density_map, binned_flow)
        t_risk = (time.perf_counter() - t_risk_start) * 1000.0
        timings["risk_ms"] = round(t_risk, 2)

        # 4. Advection Prediction & Headcount Forecasting Stage
        t_pred_start = time.perf_counter()
        predicted_risk_scores, predicted_density_maps, predicted_headcounts, inflow_rate = self.predictor.predict(
            density_map,
            binned_flow,
            current_fps=avg_fps,
            current_headcount=headcount,
            tracks=tracks
        )
        t_pred = (time.perf_counter() - t_pred_start) * 1000.0
        timings["prediction_ms"] = round(t_pred, 2)

        # 5. Digital Twin Payload Export
        digital_twin_payload = self.digital_twin.get_digital_twin_state(
            tracks=tracks,
            track_velocities=self.tracker.track_velocities,
            frame_shape=(H, W),
            camera_id=camera_id
        )

        # Build Output Contract Object strictly conforming to specification + digital twin bonus payload
        contract_output: Dict[str, Any] = {
            "timestamp": round(curr_time, 3),
            "headcount": int(headcount),
            "tracks": [
                {
                    "track_id": t["track_id"],
                    "bbox": t["bbox"],
                    "center_xy": t["center_xy"],
                    "velocity_xy": t.get("velocity_xy", [0.0, 0.0]),
                    "appearance": t.get("appearance", [])  # HSV fingerprint for cross-camera Re-ID
                }
                for t in tracks
            ],
            "flow_field": np.round(binned_flow, 3).tolist(),
            "divergence_map": np.round(divergence_map, 4).tolist(),
            "risk_score_current": round(risk_score_current, 4),
            "risk_score_predicted": predicted_risk_scores,
            "predicted_headcounts": predicted_headcounts,
            "inflow_rate_per_sec": inflow_rate,
            "digital_twin_state": digital_twin_payload
        }

        # 6. Visualization Overlay Stage
        rendered_frame = self.visualizer.render(
            frame=frame,
            tracks=tracks,
            headcount=headcount,
            binned_flow=binned_flow,
            divergence_map=divergence_map,
            risk_score=risk_score_current,
            predicted_risk=predicted_risk_scores,
            predicted_maps=predicted_density_maps,
            fps=avg_fps,
            timings=timings,
            digital_twin_engine=self.digital_twin,
            track_velocities=self.tracker.track_velocities
        )

        return contract_output, rendered_frame

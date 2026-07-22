import time
import numpy as np
from scipy.ndimage import map_coordinates
from typing import Dict, List, Tuple
from config import PredictionConfig, RiskConfig
from risk_signals import RiskEvaluator

class CrowdAdvectionPredictor:
    """
    Physically Exact Crowd Advection & Net Inflow/Outflow Headcount Forecasting Engine.
    Tracks precise person entry rates (R_in) and exit rates (R_out) across camera boundaries.
    
    Physics Formula:
    Net Rate R_net = R_in - R_out
    Predicted Headcount N(T) = max(0, Current Headcount + R_net * T)
    
    If no people enter or exit, R_net = 0.0, so N(30s) == N(60s) == N(120s) == Current Headcount.
    """
    def __init__(self, pred_config: PredictionConfig, risk_config: RiskConfig, grid_rows: int = 20, grid_cols: int = 20):
        self.pred_config = pred_config
        self.risk_config = risk_config
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.risk_evaluator = RiskEvaluator(risk_config, grid_rows=grid_rows, grid_cols=grid_cols)
        
        self.prev_active_ids = set()
        self.delta_events: List[Tuple[float, int]] = []  # (timestamp, net_person_delta)

    def advect_density(self, density_map: np.ndarray, binned_flow: np.ndarray, num_steps: int) -> np.ndarray:
        rows, cols = density_map.shape
        grid_r, grid_c = np.indices((rows, cols), dtype=np.float32)

        u_x = binned_flow[:, :, 0]
        u_y = binned_flow[:, :, 1]

        current_density = np.copy(density_map)

        for _ in range(num_steps):
            back_r = grid_r - u_y
            back_c = grid_c - u_x

            back_r = np.clip(back_r, 0, rows - 1)
            back_c = np.clip(back_c, 0, cols - 1)

            current_density = map_coordinates(
                current_density, [back_r, back_c], order=1, mode='nearest'
            )

        return current_density

    def compute_net_flow_rate(self, tracks: List[Dict]) -> float:
        """
        Calculates mathematical net person flow rate (R_net = R_in - R_out) per second over 15s window.
        """
        curr_time = time.time()
        curr_ids = {t["track_id"] for t in tracks if t.get("track_id", -1) > 0}

        if self.prev_active_ids:
            entered = len(curr_ids - self.prev_active_ids)
            exited = len(self.prev_active_ids - curr_ids)
            net_change = entered - exited

            if net_change != 0:
                self.delta_events.append((curr_time, net_change))

        self.prev_active_ids = curr_ids

        # Retain delta events from the last 15 seconds
        cutoff_time = curr_time - 15.0
        self.delta_events = [ev for ev in self.delta_events if ev[0] >= cutoff_time]

        # Calculate net rate (people per second)
        total_net_delta = sum(ev[1] for ev in self.delta_events)
        net_flow_rate = total_net_delta / 15.0

        return net_flow_rate

    def predict(
        self,
        current_density: np.ndarray,
        binned_flow: np.ndarray,
        current_fps: float,
        current_headcount: int = 0,
        tracks: List[Dict] = None
    ) -> Tuple[Dict[str, float], Dict[str, np.ndarray], Dict[str, int], float]:
        """
        Predicts density risk maps and exact future headcounts (30s, 60s, 120s).
        """
        fps = max(1.0, current_fps)
        net_rate = self.compute_net_flow_rate(tracks or [])

        predicted_risk_scores: Dict[str, float] = {}
        predicted_density_maps: Dict[str, np.ndarray] = {}
        predicted_headcounts: Dict[str, int] = {}

        substeps = self.pred_config.advection_substeps

        for sec in self.pred_config.horizons_sec:
            horizon_key = f"{sec}s"

            # 1. Physically Exact Headcount Forecast
            projected_change = int(round(net_rate * sec))
            predicted_headcounts[horizon_key] = max(0, current_headcount + projected_change)

            # 2. Semi-Lagrangian Density Advection
            total_frames = int(sec * fps)
            step_flow = binned_flow * (total_frames / float(substeps * 100.0))

            pred_density = self.advect_density(current_density, step_flow, num_steps=substeps)
            predicted_density_maps[horizon_key] = pred_density

            # 3. Physically Risk Evaluation
            risk_score, _, _, _ = self.risk_evaluator.evaluate_risk(pred_density, binned_flow)
            predicted_risk_scores[horizon_key] = round(risk_score, 2)

        return predicted_risk_scores, predicted_density_maps, predicted_headcounts, round(net_rate, 2)

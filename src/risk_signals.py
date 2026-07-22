import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from config import RiskConfig

class RiskEvaluator:
    """
    Physically Rigorous Stampede & Crowd Crush Risk Evaluator.
    
    Physics Rules:
    1. Normal Movement Is Safe: Normal walking or individual motion produces ZERO stampede risk (Risk = 0.00).
    2. Inward Convergence Requirement: Stampede crush requires multiple crowd vectors colliding INWARD into each other.
    3. Density Thresholding: Crush risk requires high local crowding (>= 3 people in close proximity).
    """
    def __init__(self, config: RiskConfig, grid_rows: int = 20, grid_cols: int = 20):
        self.config = config
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

    def compute_density_map(self, tracks: List[Dict[str, Any]], frame_shape: Tuple[int, int], binned_flow: Optional[np.ndarray] = None) -> np.ndarray:
        H, W = frame_shape
        density_map = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)

        if H <= 0 or W <= 0 or not tracks:
            return density_map

        cell_h = H / self.grid_rows
        cell_w = W / self.grid_cols
        for t in tracks:
            cx, cy = t["center_xy"]
            r = int(min(max(cy / cell_h, 0), self.grid_rows - 1))
            c = int(min(max(cx / cell_w, 0), self.grid_cols - 1))
            density_map[r, c] += 1.0

        return density_map

    def compute_divergence(self, binned_flow: np.ndarray) -> np.ndarray:
        speeds = np.hypot(binned_flow[:, :, 0], binned_flow[:, :, 1])
        valid_motion_mask = speeds > 1.2  # Significant physical speed

        u_x = np.where(valid_motion_mask, binned_flow[:, :, 0], 0.0)
        u_y = np.where(valid_motion_mask, binned_flow[:, :, 1], 0.0)

        dux_dx = np.zeros_like(u_x)
        duy_dy = np.zeros_like(u_y)

        dux_dx[:, 1:-1] = (u_x[:, 2:] - u_x[:, :-2]) / 2.0
        dux_dx[:, 0] = u_x[:, 1] - u_x[:, 0]
        dux_dx[:, -1] = u_x[:, -1] - u_x[:, -2]

        duy_dy[1:-1, :] = (u_y[2:, :] - u_y[:-2, :]) / 2.0
        duy_dy[0, :] = u_y[1, :] - u_y[0, :]
        duy_dy[-1, :] = u_y[-1, :] - u_y[-2, :]

        divergence = dux_dx + duy_dy
        return divergence

    def compute_counterflow(self, binned_flow: np.ndarray) -> np.ndarray:
        counterflow_map = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)
        
        u_x = binned_flow[:, :, 0]
        u_y = binned_flow[:, :, 1]
        speeds = np.hypot(u_x, u_y)

        for r in range(self.grid_rows):
            r_min, r_max = max(0, r - 1), min(self.grid_rows, r + 2)
            for c in range(self.grid_cols):
                if speeds[r, c] < 1.2:
                    continue

                c_min, c_max = max(0, c - 1), min(self.grid_cols, c + 2)
                patch_ux = u_x[r_min:r_max, c_min:c_max].flatten()
                patch_uy = u_y[r_min:r_max, c_min:c_max].flatten()
                patch_speeds = np.hypot(patch_ux, patch_uy)

                active_idx = patch_speeds > 1.2
                if not np.any(active_idx):
                    continue

                patch_ux = patch_ux[active_idx]
                patch_uy = patch_uy[active_idx]
                patch_mags = patch_speeds[active_idx]

                unit_ux = patch_ux / patch_mags
                unit_uy = patch_uy / patch_mags

                c_ux = u_x[r, c] / (speeds[r, c] + 1e-5)
                c_uy = u_y[r, c] / (speeds[r, c] + 1e-5)

                dots = unit_ux * c_ux + unit_uy * c_uy
                opposing = np.maximum(0.0, -dots)
                counterflow_map[r, c] = float(np.mean(opposing))

        return counterflow_map

    def evaluate_risk(self, density_map: np.ndarray, binned_flow: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates composite density-gated stampede risk score.
        Normal walking / ambient movement produces Risk = 0.00.
        """
        total_people = np.sum(density_map)

        divergence_map = self.compute_divergence(binned_flow)
        counterflow_map = self.compute_counterflow(binned_flow)
        cell_risk_map = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)

        # Normal small group (< 3 people) or low density = ZERO STAMPEDE RISK
        if total_people < 3.0:
            return 0.00, divergence_map, counterflow_map, cell_risk_map

        # Inward motion convergence
        convergence_map = np.maximum(0.0, -divergence_map)

        # Thresholding: Normal walking motion has ~0.0 to 0.4 convergence
        convergence_intensity = np.maximum(0.0, convergence_map - 0.6)
        counterflow_intensity = np.maximum(0.0, counterflow_map - 0.5)

        # Crush Risk requires high local crowding (>= 2 people in close proximity)
        density_scale = np.clip((density_map - 1.0) / 2.0, 0.0, 2.0)

        # Risk = Local Density Scale * Inward Collision Crush Intensity
        crush_factor = 0.70 * convergence_intensity + 0.30 * counterflow_intensity
        cell_risk_raw = density_scale * crush_factor

        cell_risk_map = np.clip(cell_risk_raw, 0.0, 1.0)

        max_risk = float(np.max(cell_risk_map))
        if max_risk > 0.05:
            overall_risk_score = round(min(1.0, max_risk), 2)
        else:
            overall_risk_score = 0.00

        return overall_risk_score, divergence_map, counterflow_map, cell_risk_map

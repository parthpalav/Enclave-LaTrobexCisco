import cv2
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from config import VisualizationConfig
from digital_twin import DigitalTwinEngine

class DebugVisualizer:
    """
    Renders multi-panel debug visualization overlay:
    - 1 Arrow Per Person ID accurately predicting trajectory lookahead
    - Digital Twin Overhead 2D Radar Simulation Panel
    - Divergence & stampede risk heatmap overlay (transparent on normal video)
    - Advection prediction horizon side-panels (clean dark state on empty frames)
    - Performance telemetry dashboard (stage latencies, FPS)
    """
    def __init__(self, config: VisualizationConfig, grid_rows: int = 20, grid_cols: int = 20):
        self.config = config
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

    def draw_flow_arrows(self, frame: np.ndarray, binned_flow: np.ndarray) -> np.ndarray:
        """
        Overlays vector arrows for coarse binned flow grid if enabled in config.
        """
        if not getattr(self.config, 'draw_flow_arrows', False):
            return frame

        H, W, _ = frame.shape
        cell_h = H / self.grid_rows
        cell_w = W / self.grid_cols
        stride = getattr(self.config, 'arrow_stride', 2)

        speeds = np.hypot(binned_flow[:, :, 0], binned_flow[:, :, 1])
        max_speed = np.max(speeds)
        min_motion_thresh = max(0.6, max_speed * 0.15)

        for r in range(0, self.grid_rows, stride):
            r_end = min(self.grid_rows, r + stride)
            for c in range(0, self.grid_cols, stride):
                c_end = min(self.grid_cols, c + stride)

                cx = int((c + (stride / 2.0)) * cell_w)
                cy = int((r + (stride / 2.0)) * cell_h)

                patch = binned_flow[r:r_end, c:c_end]
                dx = float(np.mean(patch[:, :, 0]))
                dy = float(np.mean(patch[:, :, 1]))

                speed = np.hypot(dx, dy)
                if speed < min_motion_thresh:
                    continue

                scale = min(5.5, max(2.5, 12.0 / (speed + 1e-3)))
                end_x = int(cx + dx * scale)
                end_y = int(cy + dy * scale)

                angle = np.arctan2(dy, dx)
                hue = int(((angle + np.pi) / (2 * np.pi)) * 180)
                color_bgr = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
                color = (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))

                cv2.circle(frame, (cx, cy), 2, color, -1, lineType=cv2.LINE_AA)
                cv2.arrowedLine(frame, (cx, cy), (end_x, end_y), color, 2, cv2.LINE_AA, 0, 0.35)

        return frame

    def draw_divergence_heatmap(self, frame: np.ndarray, divergence_map: np.ndarray, threshold: float = -0.05) -> np.ndarray:
        """
        Blends a subtle colored heatmap ONLY over high convergence cells (negative divergence).
        """
        H, W, _ = frame.shape
        conv_map = np.maximum(0.0, -divergence_map)
        max_conv = np.max(conv_map)
        
        if max_conv <= 1e-4:
            return frame

        active_mask = conv_map > 0.015
        if not np.any(active_mask):
            return frame

        norm_conv = np.zeros_like(conv_map, dtype=np.uint8)
        norm_conv[active_mask] = np.clip((conv_map[active_mask] / (max_conv + 1e-5)) * 255, 60, 255).astype(np.uint8)

        heatmap_resized = cv2.resize(norm_conv, (W, H), interpolation=cv2.INTER_LINEAR)
        heatmap_colored = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)

        alpha_mask = cv2.resize((norm_conv > 0).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        alpha_mask = cv2.GaussianBlur(alpha_mask, (15, 15), 0)[:, :, np.newaxis]

        output = frame.astype(np.float32) * (1.0 - alpha_mask * 0.40) + heatmap_colored.astype(np.float32) * (alpha_mask * 0.40)
        blended = np.clip(output, 0, 255).astype(np.uint8)

        cell_mask = cv2.resize((divergence_map < threshold).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        if np.any(cell_mask):
            contours, _ = cv2.findContours(cell_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(blended, contours, -1, (0, 0, 255), 2)

        return blended

    def draw_tracks(self, frame: np.ndarray, tracks: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draws 1 ACCURATE PREDICTIVE MOTION ARROW PER PERSON ID.
        Follows each person smoothly and projects their next position (+400ms into future).
        """
        for t in tracks:
            x1, y1, w, h = t["bbox"]
            x2, y2 = int(x1 + w), int(y1 + h)
            x1, y1 = int(x1), int(y1)
            tid = t["track_id"]
            conf = t["confidence"]
            cx, cy = int(t["center_xy"][0]), int(t["center_xy"][1])
            vx, vy = t.get("velocity_xy", [0.0, 0.0])

            # Color tied to Track ID
            color_hue = (tid * 47) % 180
            box_color = cv2.cvtColor(np.uint8([[[color_hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
            box_color = (int(box_color[0]), int(box_color[1]), int(box_color[2]))

            # Bounding box & Center core dot
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1, lineType=cv2.LINE_AA)

            # --- 1 ACCURATE PREDICTIVE ARROW PER PERSON ID ---
            speed = np.hypot(vx, vy)
            if speed > 0.2:
                lookahead_mult = min(5.0, max(2.5, 12.0 / (speed + 1e-3)))
                pred_x = int(cx + vx * lookahead_mult)
                pred_y = int(cy + vy * lookahead_mult)

                cv2.arrowedLine(frame, (cx, cy), (pred_x, pred_y), (0, 255, 255), 2, cv2.LINE_AA, 0, 0.35)
                cv2.circle(frame, (pred_x, pred_y), 5, (255, 255, 0), -1, lineType=cv2.LINE_AA)
                cv2.circle(frame, (pred_x, pred_y), 7, (0, 255, 255), 1, lineType=cv2.LINE_AA)

            label = f"ID:{tid} ({conf:.2f})"
            cv2.putText(frame, label, (x1, max(y1 - 6, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def draw_telemetry(
        self,
        frame: np.ndarray,
        headcount: int,
        fps: float,
        timings: Dict[str, float],
        risk_score: float,
        predicted_risk: Dict[str, float]
    ) -> np.ndarray:
        """
        Draws top dashboard telemetry overlay banner & bottom legend.
        """
        H, W, _ = frame.shape
        banner_h = 95
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (W, banner_h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, f"FPS: {fps:.1f}", (15, 25), font, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"Headcount: {headcount}", (140, 25), font, 0.6, (255, 255, 0), 2)
        
        risk_color = (0, 255, 0) if risk_score < 0.3 else ((0, 165, 255) if risk_score < 0.6 else (0, 0, 255))
        cv2.putText(frame, f"Current Risk: {risk_score:.2f}", (320, 25), font, 0.6, risk_color, 2)

        t_detect = timings.get("detect_track_ms", 0.0)
        t_flow = timings.get("flow_ms", 0.0)
        t_risk = timings.get("risk_ms", 0.0)
        t_pred = timings.get("prediction_ms", 0.0)
        timing_str = f"Latency Breakdown: Detect={t_detect:.1f}ms | Flow={t_flow:.1f}ms | Risk={t_risk:.1f}ms | Advect={t_pred:.1f}ms"
        cv2.putText(frame, timing_str, (15, 52), font, 0.42, (220, 220, 220), 1)

        pred_str = "Predicted Risk Horizons -> " + " | ".join([f"{k}: {v:.2f}" for k, v in predicted_risk.items()])
        cv2.putText(frame, pred_str, (15, 78), font, 0.42, (255, 200, 100), 1)

        legend_y = H - 15
        cv2.putText(frame, "Legend: Green Dots = Person Center | Yellow Arrows = 1 Arrow/ID (+400ms Prediction)", (15, legend_y), font, 0.38, (230, 230, 230), 1)

        return frame

    def render(
        self,
        frame: np.ndarray,
        tracks: List[Dict[str, Any]],
        headcount: int,
        binned_flow: np.ndarray,
        divergence_map: np.ndarray,
        risk_score: float,
        predicted_risk: Dict[str, float],
        predicted_maps: Dict[str, np.ndarray],
        fps: float,
        timings: Dict[str, float],
        digital_twin_engine: Optional[DigitalTwinEngine] = None,
        track_velocities: Optional[Dict[int, Tuple[float, float]]] = None
    ) -> np.ndarray:
        output = frame.copy()

        if self.config.draw_divergence_heatmap:
            output = self.draw_divergence_heatmap(output, divergence_map)

        if self.config.draw_flow_arrows:
            output = self.draw_flow_arrows(output, binned_flow)

        if self.config.draw_boxes:
            output = self.draw_tracks(output, tracks)

        if self.config.draw_telemetry:
            output = self.draw_telemetry(output, headcount, fps, timings, risk_score, predicted_risk)

        output = self.attach_side_panels(
            main_frame=output,
            predicted_maps=predicted_maps,
            predicted_risk=predicted_risk,
            tracks=tracks,
            track_velocities=track_velocities,
            divergence_map=divergence_map,
            digital_twin_engine=digital_twin_engine
        )

        return output

    def attach_side_panels(
        self,
        main_frame: np.ndarray,
        predicted_maps: Dict[str, np.ndarray],
        predicted_risk: Dict[str, float],
        tracks: List[Dict[str, Any]],
        track_velocities: Optional[Dict[int, Tuple[float, float]]],
        divergence_map: np.ndarray,
        digital_twin_engine: Optional[DigitalTwinEngine]
    ) -> np.ndarray:
        """
        Appends Digital Twin Overhead Radar View panel & Future Horizon Prediction heatmaps.
        FIXES EMPTY FRAME BUG: If max_d <= 1e-3, renders clean dark thumbnail instead of noisy red pattern.
        """
        H, W, _ = main_frame.shape
        side_panels = []

        # 1. Render Digital Twin Radar Panel
        if getattr(self.config, 'draw_digital_twin', True) and digital_twin_engine is not None:
            twin_canvas = digital_twin_engine.render_overhead_map(
                tracks=tracks,
                track_velocities=track_velocities or {},
                divergence_map=divergence_map,
                predicted_risk=predicted_risk,
                frame_shape=(H, W)
            )
            twin_resized = cv2.resize(twin_canvas, (240, H))
            side_panels.append(twin_resized)

        # 2. Render Future Horizons Prediction Panel
        if self.config.draw_predictions and predicted_maps:
            panel_w = 180
            pred_panel = np.zeros((H, panel_w, 3), dtype=np.uint8)
            cv2.putText(pred_panel, "Future Horizons", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            horizons = list(predicted_maps.keys())
            num_h = len(horizons)
            if num_h > 0:
                thumb_h = min(110, (H - 50) // num_h)
                thumb_w = panel_w - 30

                for idx, h_key in enumerate(horizons):
                    den_map = predicted_maps[h_key]
                    max_d = np.max(den_map)

                    # FIX: If frame has no real crowd density, render clean dark thumbnail
                    if max_d <= 1e-3:
                        thumb = np.full((thumb_h, thumb_w, 3), (25, 25, 30), dtype=np.uint8)
                        cv2.rectangle(thumb, (0, 0), (thumb_w - 1, thumb_h - 1), (60, 60, 70), 1)
                        cv2.putText(thumb, "EMPTY FRAME", (12, thumb_h // 2 + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 160), 1)
                        r_score = 0.00
                    else:
                        norm_map = (den_map / max_d * 255).astype(np.uint8)
                        thumb = cv2.applyColorMap(cv2.resize(norm_map, (thumb_w, thumb_h)), cv2.COLORMAP_JET)
                        r_score = predicted_risk.get(h_key, 0.0)

                    r_start = 45 + idx * (thumb_h + 30)
                    if r_start + thumb_h <= H:
                        pred_panel[r_start:r_start+thumb_h, 15:15+thumb_w] = thumb
                        cv2.putText(pred_panel, f"T+{h_key} (Risk: {r_score:.2f})", (15, r_start - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 255, 200), 1)

            side_panels.append(pred_panel)

        if side_panels:
            canvas = np.hstack([main_frame] + side_panels)
            return canvas

        return main_frame

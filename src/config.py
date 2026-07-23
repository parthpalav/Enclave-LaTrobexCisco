import os
import yaml
from dataclasses import dataclass, field
from typing import List

@dataclass
class DetectionConfig:
    model_name: str = "yolov8m.pt"
    conf_threshold: float = 0.15
    classes: List[int] = field(default_factory=lambda: [0])
    cadence: int = 1
    tracker_config: str = "bytetrack.yaml"

@dataclass
class OpticalFlowConfig:
    backend: str = "raft_small"
    downsample_width: int = 320
    downsample_height: int = 240
    grid_cols: int = 20
    grid_rows: int = 20

@dataclass
class RiskConfig:
    weight_density: float = 0.35
    weight_divergence: float = 0.45
    weight_counterflow: float = 0.20
    divergence_threshold: float = -0.05

@dataclass
class PredictionConfig:
    horizons_sec: List[int] = field(default_factory=lambda: [30, 60, 120])
    advection_substeps: int = 5

@dataclass
class VisualizationConfig:
    show_gui: bool = True
    draw_boxes: bool = True
    draw_flow_arrows: bool = False
    draw_divergence_heatmap: bool = True
    draw_predictions: bool = True
    draw_telemetry: bool = True
    draw_digital_twin: bool = True
    arrow_stride: int = 2

@dataclass
class PipelineConfig:
    target_fps: float = 20.0
    device: str = "cuda:0"
    log_stage_timings: bool = True
    input_source: str = "sample_crowd.mp4"
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    optical_flow: OpticalFlowConfig = field(default_factory=OpticalFlowConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    prediction: PredictionConfig = field(default_factory=PredictionConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)

def load_config(config_path: str = "config.yaml") -> PipelineConfig:
    if not os.path.exists(config_path):
        print(f"[Config] Config file '{config_path}' not found, using default configuration.")
        return PipelineConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    cfg = PipelineConfig()
    if "pipeline" in data:
        p = data["pipeline"]
        cfg.target_fps = p.get("target_fps", cfg.target_fps)
        cfg.device = p.get("device", cfg.device)
        cfg.log_stage_timings = p.get("log_stage_timings", cfg.log_stage_timings)

    if "input" in data:
        cfg.input_source = data["input"].get("source", cfg.input_source)

    if "detection" in data:
        d = data["detection"]
        cfg.detection.model_name = d.get("model_name", cfg.detection.model_name)
        cfg.detection.conf_threshold = d.get("conf_threshold", cfg.detection.conf_threshold)
        cfg.detection.classes = d.get("classes", cfg.detection.classes)
        cfg.detection.cadence = d.get("cadence", cfg.detection.cadence)
        cfg.detection.tracker_config = d.get("tracker_config", cfg.detection.tracker_config)

    if "optical_flow" in data:
        o = data["optical_flow"]
        cfg.optical_flow.backend = o.get("backend", cfg.optical_flow.backend)
        cfg.optical_flow.downsample_width = o.get("downsample_width", cfg.optical_flow.downsample_width)
        cfg.optical_flow.downsample_height = o.get("downsample_height", cfg.optical_flow.downsample_height)
        cfg.optical_flow.grid_cols = o.get("grid_cols", cfg.optical_flow.grid_cols)
        cfg.optical_flow.grid_rows = o.get("grid_rows", cfg.optical_flow.grid_rows)

    if "risk" in data:
        r = data["risk"]
        cfg.risk.weight_density = r.get("weight_density", cfg.risk.weight_density)
        cfg.risk.weight_divergence = r.get("weight_divergence", cfg.risk.weight_divergence)
        cfg.risk.weight_counterflow = r.get("weight_counterflow", cfg.risk.weight_counterflow)
        cfg.risk.divergence_threshold = r.get("divergence_threshold", cfg.risk.divergence_threshold)

    if "prediction" in data:
        pr = data["prediction"]
        cfg.prediction.horizons_sec = pr.get("horizons_sec", cfg.prediction.horizons_sec)
        cfg.prediction.advection_substeps = pr.get("advection_substeps", cfg.prediction.advection_substeps)

    if "visualization" in data:
        v = data["visualization"]
        cfg.visualization.show_gui = v.get("show_gui", cfg.visualization.show_gui)
        cfg.visualization.draw_boxes = v.get("draw_boxes", cfg.visualization.draw_boxes)
        cfg.visualization.draw_flow_arrows = v.get("draw_flow_arrows", cfg.visualization.draw_flow_arrows)
        cfg.visualization.draw_divergence_heatmap = v.get("draw_divergence_heatmap", cfg.visualization.draw_divergence_heatmap)
        cfg.visualization.draw_predictions = v.get("draw_predictions", cfg.visualization.draw_predictions)
        cfg.visualization.draw_telemetry = v.get("draw_telemetry", cfg.visualization.draw_telemetry)
        cfg.visualization.draw_digital_twin = v.get("draw_digital_twin", cfg.visualization.draw_digital_twin)
        cfg.visualization.arrow_stride = v.get("arrow_stride", cfg.visualization.arrow_stride)

    return cfg

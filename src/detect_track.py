import time
import numpy as np
import torch
import cv2
from typing import List, Dict, Any, Tuple
from ultralytics import YOLO
from config import DetectionConfig


def compute_appearance_fingerprint(frame: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> List[float]:
    """
    Computes a compact 24-bin HSV color histogram over the upper-body region of a detected person.
    Used for cross-camera appearance-based Re-ID to deduplicate headcounts.
    Returns a 24-element L2-normalised float list, or empty list if region is invalid.
    """
    h, w = frame.shape[:2]
    px1, py1 = max(0, int(x1)), max(0, int(y1))
    px2, py2 = min(w, int(x2)), min(h, int(y2))
    if px2 <= px1 or py2 <= py1:
        return []
    # Focus on upper 60% of bbox (torso/head - more discriminative, less affected by occlusion)
    upper_y2 = py1 + max(1, int((py2 - py1) * 0.60))
    crop = frame[py1:upper_y2, px1:px2]
    if crop.size == 0:
        return []
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # 8-bin H, 8-bin S, 8-bin V = 24 bins total
    hist_h = cv2.calcHist([hsv], [0], None, [8], [0, 180]).flatten()
    hist_s = cv2.calcHist([hsv], [1], None, [8], [0, 256]).flatten()
    hist_v = cv2.calcHist([hsv], [2], None, [8], [0, 256]).flatten()
    feat = np.concatenate([hist_h, hist_s, hist_v]).astype(np.float32)
    norm = np.linalg.norm(feat)
    if norm > 1e-5:
        feat = feat / norm
    return feat.tolist()

class PersonTracker:
    """
    Person detection and tracking stage using YOLOv8 and ByteTrack.
    Computes per-person smoothed motion velocity vectors for 1-arrow per ID trajectory prediction.
    """
    def __init__(self, config: DetectionConfig, device: str = "cuda:0"):
        self.config = config
        self.device = device if torch.cuda.is_available() else "cpu"
        print(f"[DetectTrack] Initializing YOLOv8 model ({config.model_name}) on device {self.device}...")
        self.model = YOLO(config.model_name)
        self.model.to(self.device)
        
        self.frame_count = 0
        self.last_tracks: List[Dict[str, Any]] = []
        self.track_history: Dict[int, List[Tuple[float, float, float]]] = {}
        self.track_velocities: Dict[int, Tuple[float, float]] = {}
        self.last_inference_time_ms: float = 0.0

    def process_frame(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], int, float]:
        """
        Process a single image frame (BGR format from OpenCV).
        Returns:
            tracks: List of dicts with track_id, bbox, center_xy, confidence, velocity_xy
            headcount: count of detected/tracked persons
            inference_time_ms: processing time for this stage in milliseconds
        """
        self.frame_count += 1
        start_time = time.perf_counter()
        curr_timestamp = time.time()

        # Check cadence
        if (self.frame_count - 1) % self.config.cadence != 0 and self.last_tracks:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return self.last_tracks, len(self.last_tracks), elapsed_ms

        results = None
        try:
            results = self.model.track(
                source=frame,
                conf=self.config.conf_threshold,
                classes=self.config.classes,
                tracker=self.config.tracker_config,
                persist=True,
                verbose=False,
                device=self.device
            )
        except Exception as err:
            # Fallback to standard detect prediction if tracker encounters an issue
            results = self.model.predict(
                source=frame,
                conf=self.config.conf_threshold,
                classes=self.config.classes,
                verbose=False,
                device=self.device
            )

        tracks = []
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.cpu().numpy()
                for idx, box in enumerate(boxes):
                    xywh = box.xywh[0]
                    xyxy = box.xyxy[0]
                    # Ensure positive integer track_id so detections are never discarded
                    track_id = int(box.id[0]) if (box.id is not None and len(box.id) > 0) else (idx + 1)
                    conf = float(box.conf[0])

                    x1, y1, x2, y2 = xyxy
                    w = x2 - x1
                    h = y2 - y1

                    center_x = float(xywh[0])
                    center_y = float(xywh[1])

                    # Calculate per-person track velocity from motion history
                    vx, vy = 0.0, 0.0
                    if track_id in self.track_history and len(self.track_history[track_id]) > 0:
                        prev_cx, prev_cy, prev_t = self.track_history[track_id][-1]
                        dt = max(curr_timestamp - prev_t, 1e-3)

                        # Raw displacement delta
                        raw_vx = (center_x - prev_cx)
                        raw_vy = (center_y - prev_cy)

                        # Exponential Moving Average (EMA) velocity smoothing
                        prev_vx, prev_vy = self.track_velocities.get(track_id, (raw_vx, raw_vy))
                        vx = 0.65 * raw_vx + 0.35 * prev_vx
                        vy = 0.65 * raw_vy + 0.35 * prev_vy

                    self.track_velocities[track_id] = (vx, vy)

                    # Maintain history
                    if track_id not in self.track_history:
                        self.track_history[track_id] = []
                    self.track_history[track_id].append((center_x, center_y, curr_timestamp))
                    if len(self.track_history[track_id]) > 15:
                        self.track_history[track_id].pop(0)

                    # Compute appearance fingerprint for cross-camera Re-ID
                    appearance = compute_appearance_fingerprint(frame, x1, y1, x2, y2)

                    tracks.append({
                        "track_id": track_id,
                        "bbox": [round(float(x1), 1), round(float(y1), 1), round(float(w), 1), round(float(h), 1)],
                        "center_xy": [round(center_x, 1), round(center_y, 1)],
                        "velocity_xy": [round(vx, 2), round(vy, 2)],
                        "confidence": round(conf, 3),
                        "appearance": appearance   # 24-bin HSV fingerprint for Re-ID
                    })

        self.last_tracks = tracks
        self.last_inference_time_ms = (time.perf_counter() - start_time) * 1000.0
        headcount = len(tracks)

        return tracks, headcount, self.last_inference_time_ms

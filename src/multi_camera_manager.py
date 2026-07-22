import cv2
import time
import threading
import queue
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from config import load_config, PipelineConfig
from pipeline import CrowdFlowPipeline

# ─────────────────────────────────────────────────────────────────
# Spatial zone registry: maps camera_id → zone rect in digital twin
# (x_offset, y_offset, width, height) as fractions of 0.0–1.0
# Each camera covers a separate tile in the 2D overhead floor plan.
# Add more zones here as you connect more cameras/phones.
# ─────────────────────────────────────────────────────────────────
CAMERA_ZONES = {
    "cam_1":        {"label": "Zone A — Main Laptop",  "x": 0.0,  "y": 0.0,  "w": 0.5, "h": 0.5},
    "cam_2":        {"label": "Zone B — Secondary",    "x": 0.5,  "y": 0.0,  "w": 0.5, "h": 0.5},
}
# Any phone/extra cam that connects auto-gets the next zone slot
_EXTRA_ZONE_SLOTS = [
    {"x": 0.0,  "y": 0.5, "w": 0.5, "h": 0.5},   # Zone C
    {"x": 0.5,  "y": 0.5, "w": 0.5, "h": 0.5},   # Zone D
    {"x": 0.0,  "y": 0.0, "w": 0.33,"h": 0.5},   # Zone E
    {"x": 0.33, "y": 0.0, "w": 0.34,"h": 0.5},   # Zone F
]
_extra_slot_index = 0
_zone_lock = threading.Lock()


def get_or_assign_zone(camera_id: str) -> dict:
    """Returns spatial zone for a camera, assigning a new slot if unknown."""
    global _extra_slot_index
    if camera_id in CAMERA_ZONES:
        return CAMERA_ZONES[camera_id]
    with _zone_lock:
        if camera_id not in CAMERA_ZONES:
            slot_idx = _extra_slot_index % len(_EXTRA_ZONE_SLOTS)
            slot = _EXTRA_ZONE_SLOTS[slot_idx]
            _extra_slot_index += 1
            label = f"Zone {chr(65 + slot_idx + 2)} — {camera_id}"
            CAMERA_ZONES[camera_id] = {"label": label, **slot}
        return CAMERA_ZONES[camera_id]


class CameraWorker(threading.Thread):
    """
    Independent worker thread processing single camera stream.
    Supports: USB webcam, RTSP, HTTP MJPEG, or push_stream (secondary laptop / phone).
    """
    def __init__(self, camera_id: str, name: str, source: Any, config: PipelineConfig):
        super().__init__()
        self.camera_id = camera_id
        self.name = name
        self.source = source
        self.config = config
        self.pipeline = CrowdFlowPipeline(config)
        self.zone = get_or_assign_zone(camera_id)

        self.running = False
        self.frame_queue = queue.Queue(maxsize=5)
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_rendered_frame: Optional[np.ndarray] = None
        self.latest_contract: Dict[str, Any] = {}
        self.last_heartbeat: float = time.time()
        self.lock = threading.Lock()
        self.daemon = True

    def push_frame(self, frame: np.ndarray):
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        self.frame_queue.put(frame)

    def run(self):
        self.running = True
        print(f"[MultiCam] Starting worker '{self.name}' ({self.camera_id}) → {self.zone['label']}")

        is_push_stream = str(self.source).startswith("push_stream") or str(self.source).startswith("browser_stream")
        cap = None
        if not is_push_stream:
            source_input = int(self.source) if str(self.source).isdigit() else self.source
            cap = cv2.VideoCapture(source_input)

        while self.running:
            try:
                if is_push_stream:
                    try:
                        frame = self.frame_queue.get(timeout=0.2)
                    except queue.Empty:
                        time.sleep(0.05)
                        continue
                else:
                    if cap is None or not cap.isOpened():
                        time.sleep(0.1)
                        continue
                    ret, frame = cap.read()
                    if not ret:
                        time.sleep(0.05)
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue

                    if str(self.source).isdigit():
                        frame = cv2.flip(frame, 1)

                contract_output, rendered_frame = self.pipeline.process_frame(frame)

                # Inject zone info into the contract so the digital twin knows where to plot
                if contract_output and "digital_twin_state" in contract_output:
                    contract_output["digital_twin_state"]["zone"] = self.zone

                with self.lock:
                    self.latest_raw_frame = frame
                    self.latest_rendered_frame = rendered_frame
                    self.latest_contract = contract_output

            except Exception as e:
                print(f"[MultiCam] Exception in worker '{self.name}': {e}")
                time.sleep(0.05)

            time.sleep(0.01)

        if cap is not None:
            cap.release()
        print(f"[MultiCam] Worker stopped: '{self.name}'.")

    def get_latest_data(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        with self.lock:
            return self.latest_rendered_frame, self.latest_contract.copy()

    def stop(self):
        self.running = False


class MultiCameraManager:
    """
    Orchestrates multiple camera workers, aggregating real headcount predictions,
    digital twin spatial states, and risk alarms.
    """
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.base_config = load_config(config_path)
        self.workers: Dict[str, CameraWorker] = {}
        self.lock = threading.Lock()

    def _add_camera_nolock(self, camera_id: str, name: str, source: Any) -> bool:
        """Internal: add camera WITHOUT acquiring lock (caller must hold it)."""
        if camera_id in self.workers:
            return False
        cam_config = load_config(self.config_path)
        cam_config.input_source = str(source)
        worker = CameraWorker(camera_id, name, source, cam_config)
        self.workers[camera_id] = worker
        worker.start()
        return True

    def add_camera(self, camera_id: str, name: str, source: Any) -> bool:
        """Public: add a camera (acquires lock)."""
        with self.lock:
            return self._add_camera_nolock(camera_id, name, source)

    def push_laptop_frame(self, camera_id: str, frame: np.ndarray):
        """
        Receives a frame from a secondary laptop or phone stream.
        Fixed: no longer holds self.lock while calling add_camera (deadlock fix).
        """
        # Check and register without holding lock during add_camera
        with self.lock:
            if camera_id not in self.workers:
                needs_register = True
                cam_num = len(self.workers) + 1
            else:
                needs_register = False
                cam_num = None

        if needs_register:
            display_name = f"Camera {cam_num} ({camera_id})"
            self.add_camera(camera_id, display_name, f"push_stream:{camera_id}")
            print(f"[MultiCam] New push-stream device registered: {display_name} → {CAMERA_ZONES.get(camera_id, {}).get('label','?')}")

        with self.lock:
            if camera_id in self.workers:
                self.workers[camera_id].push_frame(frame)

    def remove_camera(self, camera_id: str):
        with self.lock:
            if camera_id in self.workers:
                self.workers[camera_id].stop()
                del self.workers[camera_id]

    def get_global_analytics(self) -> Dict[str, Any]:
        total_headcount = 0
        max_risk = 0.0
        predicted_30s = 0
        predicted_60s = 0
        predicted_120s = 0
        all_avatars = []
        camera_summaries = []

        with self.lock:
            workers_snapshot = list(self.workers.items())

        for cam_id, worker in workers_snapshot:
            _, contract = worker.get_latest_data()

            hc = contract.get("headcount", 0) if contract else 0
            total_headcount += hc

            c_risk = contract.get("risk_score_current", 0.0) if contract else 0.0
            max_risk = max(max_risk, c_risk)

            p_risk = contract.get("risk_score_predicted", {}) if contract else {}
            p_headcounts = contract.get("predicted_headcounts", {}) if contract else {}

            predicted_30s += p_headcounts.get("30s", hc)
            predicted_60s += p_headcounts.get("60s", hc)
            predicted_120s += p_headcounts.get("120s", hc)

            zone = worker.zone
            if contract:
                dt_state = contract.get("digital_twin_state", {})
                avatars = dt_state.get("avatars", [])
                for av in avatars:
                    # Map avatar coords into the camera's zone in the global floor plan
                    av["camera_id"] = cam_id
                    av["zone"] = zone
                    # Transform avatar local position (0-1) into global twin canvas position
                    av["twin_x"] = zone["x"] + av.get("x", 0.5) * zone["w"]
                    av["twin_y"] = zone["y"] + av.get("y", 0.5) * zone["h"]
                    all_avatars.append(av)

            camera_summaries.append({
                "camera_id": cam_id,
                "name": worker.name,
                "headcount": hc,
                "risk_current": c_risk,
                "risk_30s": p_risk.get("30s", 0.0),
                "zone": zone
            })

        alerts = []
        if max_risk > 0.60:
            alerts.append({"level": "CRITICAL", "message": f"High stampede risk detected (Risk Score: {max_risk:.2f})!"})
        if predicted_120s > total_headcount + 5 and total_headcount > 0:
            alerts.append({"level": "WARNING", "message": f"Inflow increase predicted in 120s (~{predicted_120s} people expected)!"})

        return {
            "global_headcount": total_headcount,
            "global_max_risk": round(max_risk, 2),
            "predicted_headcounts": {
                "30s": predicted_30s,
                "60s": predicted_60s,
                "120s": predicted_120s
            },
            "active_cameras_count": len(workers_snapshot),
            "cameras": camera_summaries,
            "digital_twin_avatars": all_avatars,
            "alerts": alerts,
            "camera_zones": CAMERA_ZONES
        }

    def stop_all(self):
        with self.lock:
            for worker in self.workers.values():
                worker.stop()
            self.workers.clear()

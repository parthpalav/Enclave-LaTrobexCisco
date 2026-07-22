import cv2
import time
import threading
import queue
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from config import load_config, PipelineConfig
from pipeline import CrowdFlowPipeline

class CameraWorker(threading.Thread):
    """
    Independent worker thread processing single camera stream (USB webcam, RTSP, HTTP stream, or Secondary Laptop Stream).
    """
    def __init__(self, camera_id: str, name: str, source: Any, config: PipelineConfig):
        super().__init__()
        self.camera_id = camera_id
        self.name = name
        self.source = source
        self.config = config
        self.pipeline = CrowdFlowPipeline(config)
        
        self.running = False
        self.frame_queue = queue.Queue(maxsize=5)
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_rendered_frame: Optional[np.ndarray] = None
        self.latest_contract: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.daemon = True

    def push_frame(self, frame: np.ndarray):
        """
        Pushes frame received from secondary laptop camera stream into processing queue.
        """
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        self.frame_queue.put(frame)

    def run(self):
        self.running = True
        print(f"[MultiCam] Starting worker thread for Camera '{self.name}' ({self.camera_id}) -> Source: {self.source}")
        
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
        print(f"[MultiCam] Worker thread stopped for Camera '{self.name}'.")

    def get_latest_data(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        with self.lock:
            return self.latest_rendered_frame, self.latest_contract.copy()

    def stop(self):
        self.running = False


class MultiCameraManager:
    """
    Orchestrates multiple camera workers, aggregating real mathematical headcount predictions,
    digital twin states, and risk alarms without superficial multipliers.
    """
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.base_config = load_config(config_path)
        self.workers: Dict[str, CameraWorker] = {}
        self.lock = threading.Lock()

    def add_camera(self, camera_id: str, name: str, source: Any) -> bool:
        with self.lock:
            if camera_id in self.workers:
                return False

            cam_config = load_config(self.config_path)
            cam_config.input_source = str(source)
            
            worker = CameraWorker(camera_id, name, source, cam_config)
            self.workers[camera_id] = worker
            worker.start()
            return True

    def push_laptop_frame(self, camera_id: str, frame: np.ndarray):
        with self.lock:
            if camera_id not in self.workers:
                cam_num = len(self.workers) + 1
                self.add_camera(camera_id, f"Camera {cam_num}", f"push_stream:{camera_id}")
            self.workers[camera_id].push_frame(frame)

    def remove_camera(self, camera_id: str):
        with self.lock:
            if camera_id in self.workers:
                self.workers[camera_id].stop()
                del self.workers[camera_id]

    def get_global_analytics(self) -> Dict[str, Any]:
        """
        Aggregates REAL mathematical analytics across active connected cameras only.
        Reports all registered camera workers immediately.
        """
        total_headcount = 0
        max_risk = 0.0
        predicted_30s = 0
        predicted_60s = 0
        predicted_120s = 0
        all_avatars = []
        camera_summaries = []

        with self.lock:
            for cam_id, worker in self.workers.items():
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

                if contract:
                    dt_state = contract.get("digital_twin_state", {})
                    avatars = dt_state.get("avatars", [])
                    for av in avatars:
                        av["camera_id"] = cam_id
                        all_avatars.append(av)

                camera_summaries.append({
                    "camera_id": cam_id,
                    "name": worker.name,
                    "headcount": hc,
                    "risk_current": c_risk,
                    "risk_30s": p_risk.get("30s", 0.0)
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
            "active_cameras_count": len(self.workers),
            "cameras": camera_summaries,
            "digital_twin_avatars": all_avatars,
            "alerts": alerts
        }

    def stop_all(self):
        with self.lock:
            for worker in self.workers.values():
                worker.stop()
            self.workers.clear()

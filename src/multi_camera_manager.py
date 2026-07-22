import cv2
import time
import threading
import queue
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from config import load_config, PipelineConfig
from pipeline import CrowdFlowPipeline


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two L2-normalised vectors. Returns -1 to 1."""
    if not a or not b or len(a) != len(b):
        return 0.0
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom < 1e-8:
        return 0.0
    return float(np.dot(va, vb) / denom)


def deduplicate_global_tracks(all_camera_tracks: List[Dict]) -> int:
    """
    Cross-camera deduplication using HSV appearance fingerprint cosine similarity.
    Groups tracks from different cameras that likely represent the same physical person.

    Logic:
    - Collects all (camera_id, track) pairs
    - Computes pairwise cosine similarity of appearance fingerprints between tracks
      from DIFFERENT cameras
    - If similarity >= REID_THRESHOLD, marks the pair as the same person (duplicate)
    - Uses Union-Find to cluster duplicates
    - Returns unique_count = total_tracks - number_of_duplicates_merged

    REID_THRESHOLD = 0.90 (high threshold to avoid false merges)
    """
    REID_THRESHOLD = 0.90

    if not all_camera_tracks:
        return 0

    n = len(all_camera_tracks)
    # Union-Find
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for i in range(n):
        for j in range(i + 1, n):
            cam_i = all_camera_tracks[i]["camera_id"]
            cam_j = all_camera_tracks[j]["camera_id"]
            # Only try to merge tracks from DIFFERENT cameras
            if cam_i == cam_j:
                continue
            feat_i = all_camera_tracks[i].get("appearance", [])
            feat_j = all_camera_tracks[j].get("appearance", [])
            if not feat_i or not feat_j:
                continue
            sim = cosine_similarity(feat_i, feat_j)
            if sim >= REID_THRESHOLD:
                union(i, j)

    unique_clusters = len(set(find(i) for i in range(n)))
    return unique_clusters

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
        self.last_frame_time: float = time.time()   # updated every frame received
        self.is_push_stream: bool = str(source).startswith("push_stream") or str(source).startswith("browser_stream")
        self.lock = threading.Lock()
        self.daemon = True

    def push_frame(self, frame: np.ndarray):
        self.last_frame_time = time.time()   # mark activity
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        self.frame_queue.put(frame)

    def run(self):
        self.running = True
        print(f"[MultiCam] Starting worker '{self.name}' ({self.camera_id}) → {self.zone['label']}")

        is_push_stream = self.is_push_stream
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
                    self.last_frame_time = time.time()   # mark activity for non-push streams

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

        # Background thread: evicts push-stream cameras that go silent
        self._cleanup_thread = threading.Thread(target=self._cleanup_stale_workers, daemon=True)
        self._cleanup_thread.start()

    STALE_TIMEOUT_SEC = 10.0   # seconds of silence before removing a push-stream device

    def _cleanup_stale_workers(self):
        """Runs every 5s. Removes push-stream workers that haven't sent a frame recently."""
        while True:
            time.sleep(5)
            now = time.time()
            to_remove = []
            with self.lock:
                for cam_id, worker in self.workers.items():
                    if worker.is_push_stream:
                        silent_for = now - worker.last_frame_time
                        if silent_for > self.STALE_TIMEOUT_SEC:
                            to_remove.append(cam_id)
            for cam_id in to_remove:
                print(f"[MultiCam] Device '{cam_id}' timed out ({self.STALE_TIMEOUT_SEC}s silence). Removing.")
                self.remove_camera(cam_id)

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
        max_risk = 0.0
        predicted_30s = 0
        predicted_60s = 0
        predicted_120s = 0
        all_avatars = []
        camera_summaries = []
        all_tracks_global: List[Dict] = []   # for cross-camera Re-ID

        with self.lock:
            workers_snapshot = list(self.workers.items())

        for cam_id, worker in workers_snapshot:
            _, contract = worker.get_latest_data()

            hc = contract.get("headcount", 0) if contract else 0

            c_risk = contract.get("risk_score_current", 0.0) if contract else 0.0
            max_risk = max(max_risk, c_risk)

            p_risk = contract.get("risk_score_predicted", {}) if contract else {}
            p_headcounts = contract.get("predicted_headcounts", {}) if contract else {}

            predicted_30s += p_headcounts.get("30s", hc)
            predicted_60s += p_headcounts.get("60s", hc)
            predicted_120s += p_headcounts.get("120s", hc)

            # Collect tracks with camera_id for global Re-ID deduplication
            if contract:
                for t in contract.get("tracks", []):
                    all_tracks_global.append({
                        "camera_id": cam_id,
                        "track_id": t.get("track_id"),
                        "appearance": t.get("appearance", []),
                    })

            zone = worker.zone
            if contract:
                dt_state = contract.get("digital_twin_state", {})
                avatars = dt_state.get("avatars", [])
                for av in avatars:
                    av["camera_id"] = cam_id
                    av["zone"] = zone
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

        # Cross-camera Re-ID: deduplicate people visible in multiple cameras
        if len(workers_snapshot) > 1 and all_tracks_global:
            unique_headcount = deduplicate_global_tracks(all_tracks_global)
        else:
            unique_headcount = sum(c.get("headcount", 0) for c in camera_summaries)

        alerts = []
        if max_risk > 0.60:
            alerts.append({"level": "CRITICAL", "message": f"High stampede risk detected (Risk Score: {max_risk:.2f})!"})
        if predicted_120s > unique_headcount + 5 and unique_headcount > 0:
            alerts.append({"level": "WARNING", "message": f"Inflow increase predicted in 120s (~{predicted_120s} people expected)!"})

        return {
            "global_headcount": unique_headcount,
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

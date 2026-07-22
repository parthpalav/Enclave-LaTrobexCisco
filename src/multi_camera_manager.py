import cv2
import time
import threading
import queue
import json
import os
import numpy as np
from collections import deque
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


def deduplicate_global_tracks(all_camera_tracks: List[Dict], cam_zones: Dict[str, dict] = None) -> int:
    """
    Cross-camera deduplication using HSV appearance fingerprint cosine similarity.
    Only compares tracks from cameras whose zones GEOMETRICALLY OVERLAP.
    Non-overlapping zones cannot share the same person — no comparison needed.

    REID_THRESHOLD = 0.75  (lower = more aggressive merging)
    """
    REID_THRESHOLD = 0.75

    if not all_camera_tracks:
        return 0

    n = len(all_camera_tracks)
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
            if cam_i == cam_j:
                continue
            # Skip dedup entirely if zones don't overlap
            if cam_zones:
                zi = cam_zones.get(cam_i) or all_camera_tracks[i].get("zone")
                zj = cam_zones.get(cam_j) or all_camera_tracks[j].get("zone")
                if zi and zj and not zones_overlap(zi, zj):
                    continue
            feat_i = all_camera_tracks[i].get("appearance", [])
            feat_j = all_camera_tracks[j].get("appearance", [])
            if not feat_i or not feat_j:
                continue
            if cosine_similarity(feat_i, feat_j) >= REID_THRESHOLD:
                union(i, j)

    return len(set(find(i) for i in range(n)))


# ─────────────────────────────────────────────────────────────────
# Spatial zone registry: maps camera_id → zone rect in digital twin
# (x_offset, y_offset, width, height) as fractions of 0.0–1.0
# Each camera covers a separate tile in the 2D overhead floor plan.
# Add more zones here as you connect more cameras/phones.
# ─────────────────────────────────────────────────────────────────
MAX_CCTV_DEVICES = 4
PRIMARY_CAMERA_ID = "cam_1"
STAMPEDE_RISK_THRESHOLD = 0.60
STAMPEDE_PREDICTED_INCREASE = 5
STAMPEDE_HEADCOUNT_THRESHOLD = 2
GLOBAL_DUPLICATE_DISTANCE = 0.08
GLOBAL_REID_THRESHOLD = 0.75
_DEVICE_SLOTS = [
    {"slot": "A", "label": "Camera A", "x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5},
    {"slot": "B", "label": "Camera B", "x": 0.5, "y": 0.0, "w": 0.5, "h": 0.5},
    {"slot": "C", "label": "Camera C", "x": 0.0, "y": 0.5, "w": 0.5, "h": 0.5},
    {"slot": "D", "label": "Camera D", "x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5},
]
CAMERA_ZONES: Dict[str, dict] = {}
_zone_lock = threading.Lock()
_SLOT_REGISTRY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "cctv_device_slots.json",
)


def _load_camera_zones() -> Dict[str, dict]:
    """Load stable CCTV slot assignments without trusting malformed registry data."""
    if not os.path.exists(_SLOT_REGISTRY_FILE):
        return {}
    try:
        with open(_SLOT_REGISTRY_FILE, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        slots_by_id = saved.get("slots", {})
        valid_slots = {slot["slot"]: slot for slot in _DEVICE_SLOTS}
        result = {}
        for camera_id, slot in slots_by_id.items():
            slot_id = slot.get("slot") if isinstance(slot, dict) else None
            if isinstance(camera_id, str) and slot_id in valid_slots:
                result[camera_id] = dict(valid_slots[slot_id])
        return result
    except (OSError, ValueError, TypeError):
        return {}


def _save_camera_zones() -> None:
    os.makedirs(os.path.dirname(_SLOT_REGISTRY_FILE), exist_ok=True)
    temporary_path = _SLOT_REGISTRY_FILE + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump({"version": 1, "slots": CAMERA_ZONES}, handle, indent=2)
    os.replace(temporary_path, _SLOT_REGISTRY_FILE)


CAMERA_ZONES.update(_load_camera_zones())


def get_or_assign_zone(camera_id: str) -> dict:
    """Returns a stable A-D coverage slot for a camera in this server session."""
    if camera_id in CAMERA_ZONES:
        return CAMERA_ZONES[camera_id]
    with _zone_lock:
        if camera_id not in CAMERA_ZONES:
            used_slots = {zone["slot"] for zone in CAMERA_ZONES.values()}
            slot = next((item for item in _DEVICE_SLOTS if item["slot"] not in used_slots), None)
            if slot is None:
                raise ValueError(f"Maximum of {MAX_CCTV_DEVICES} CCTV devices reached")
            CAMERA_ZONES[camera_id] = dict(slot)
            _save_camera_zones()
        return CAMERA_ZONES[camera_id]


def zones_overlap(z1: dict, z2: dict) -> bool:
    """Returns True if two zone rects share any area (AABB intersection test)."""
    return (z1["x"] < z2["x"] + z2["w"] and z1["x"] + z1["w"] > z2["x"] and
            z1["y"] < z2["y"] + z2["h"] and z1["y"] + z1["h"] > z2["y"])


def merge_duplicate_avatars(avatars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse obvious duplicate people from overlapping cameras into one twin entity."""
    merged: List[Dict[str, Any]] = []
    for avatar in avatars:
        duplicate_of = None
        for existing in merged:
            if avatar.get("camera_id") == existing.get("camera_id"):
                continue
            z1, z2 = avatar.get("zone"), existing.get("zone")
            dx = float(avatar.get("twin_x", 0.0)) - float(existing.get("twin_x", 0.0))
            dy = float(avatar.get("twin_y", 0.0)) - float(existing.get("twin_y", 0.0))
            distance = float(np.hypot(dx, dy))
            looks_same = cosine_similarity(avatar.get("appearance", []), existing.get("appearance", [])) >= GLOBAL_REID_THRESHOLD
            spatially_same = distance <= GLOBAL_DUPLICATE_DISTANCE
            if (z1 and z2 and zones_overlap(z1, z2) and looks_same) or spatially_same:
                duplicate_of = existing
                break
        if duplicate_of is not None:
            avatar["avatar_id"] = duplicate_of.get("avatar_id", avatar.get("avatar_id"))
            duplicate_of.setdefault("source_cameras", [duplicate_of.get("camera_id")])
            if avatar.get("camera_id") not in duplicate_of["source_cameras"]:
                duplicate_of["source_cameras"].append(avatar.get("camera_id"))
            duplicate_of["merged_duplicate_count"] = duplicate_of.get("merged_duplicate_count", 0) + 1
        else:
            avatar["source_cameras"] = [avatar.get("camera_id")]
            merged.append(avatar)
    return merged


class GlobalIDRegistry:
    """
    Manages a global pool of sequential person IDs across all cameras.

    When a (camera_id, local_track_id) is seen for the first time, it is assigned
    the lowest available global ID. When it disappears from ALL cameras, the global
    ID is returned to the free pool and reassigned to the next new person.

    This prevents IDs growing unboundedly and resets them cleanly.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._local_to_global: Dict[tuple, int] = {}   # (cam_id, local_id) -> global_id
        self._global_active: set = set()               # currently assigned global IDs
        self._next_id: int = 1                         # monotonic counter for new IDs
        self._free_pool: List[int] = []                # recycled IDs (lowest first)

    def _alloc(self) -> int:
        if self._free_pool:
            return self._free_pool.pop(0)
        gid = self._next_id
        self._next_id += 1
        return gid

    def update(self, active_tracks: Dict[str, List[int]]) -> Dict[tuple, int]:
        """
        active_tracks: {camera_id: [local_track_id, ...]} for all cameras this frame.
        Returns mapping (cam_id, local_id) -> global_id for all currently active tracks.
        """
        with self._lock:
            current_keys = set()
            for cam_id, local_ids in active_tracks.items():
                for lid in local_ids:
                    key = (cam_id, lid)
                    current_keys.add(key)
                    if key not in self._local_to_global:
                        gid = self._alloc()
                        self._local_to_global[key] = gid
                        self._global_active.add(gid)

            # Release IDs for tracks that disappeared from ALL cameras
            gone_keys = set(self._local_to_global) - current_keys
            for key in gone_keys:
                gid = self._local_to_global.pop(key)
                self._global_active.discard(gid)
                self._free_pool.append(gid)
            self._free_pool.sort()

            return dict(self._local_to_global)


# Singleton registry shared across all camera workers
_global_id_registry = GlobalIDRegistry()



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
        self.frame_queue = queue.Queue(maxsize=1)
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_rendered_frame: Optional[np.ndarray] = None
        self.latest_contract: Dict[str, Any] = {}
        self.last_heartbeat: float = time.time()
        self.last_frame_time: float = time.time()   # updated every frame received
        self.last_processed_time: float = 0.0
        self.frames_received: int = 0
        self.frames_processed: int = 0
        self.frames_dropped: int = 0
        self.frame_arrival_times = deque(maxlen=30)
        self.frame_processed_times = deque(maxlen=30)
        self.is_push_stream: bool = str(source).startswith("push_stream") or str(source).startswith("browser_stream")
        self.lock = threading.Lock()
        self.daemon = True

    def push_frame(self, frame: np.ndarray):
        now = time.time()
        with self.lock:
            self.last_frame_time = now
            self.frames_received += 1
            self.frame_arrival_times.append(now)
            self.latest_raw_frame = frame
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                    self.frames_dropped += 1
                except queue.Empty:
                    break
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

                contract_output, rendered_frame = self.pipeline.process_frame(frame, camera_id=self.camera_id)

                # Inject zone info into the contract so the digital twin knows where to plot
                if contract_output and "digital_twin_state" in contract_output:
                    contract_output["digital_twin_state"]["zone"] = self.zone

                with self.lock:
                    self.last_processed_time = time.time()
                    self.frames_processed += 1
                    self.frame_processed_times.append(self.last_processed_time)
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

    def get_stream_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            if self.is_push_stream and self.latest_raw_frame is not None:
                return self.latest_raw_frame.copy()
            if self.latest_rendered_frame is not None:
                return self.latest_rendered_frame.copy()
            return self.latest_raw_frame.copy() if self.latest_raw_frame is not None else None

    @staticmethod
    def _rate(timestamps: deque) -> float:
        if len(timestamps) < 2:
            return 0.0
        elapsed = timestamps[-1] - timestamps[0]
        return round((len(timestamps) - 1) / elapsed, 1) if elapsed > 1e-3 else 0.0

    def get_health(self) -> Dict[str, Any]:
        """Snapshot transport and inference health for the control-room UI."""
        with self.lock:
            age = time.time() - self.last_frame_time
            return {
                "status": "LIVE" if age <= 3.0 else "STALE",
                "last_frame_age_sec": round(age, 1),
                "input_fps": self._rate(self.frame_arrival_times),
                "processing_fps": self._rate(self.frame_processed_times),
                "frames_received": self.frames_received,
                "frames_processed": self.frames_processed,
                "frames_dropped": self.frames_dropped,
            }

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
        if len(self.workers) >= MAX_CCTV_DEVICES:
            print(f"[MultiCam] Rejecting '{camera_id}': maximum of {MAX_CCTV_DEVICES} CCTV devices reached.")
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

    def push_laptop_frame(self, camera_id: str, frame: np.ndarray, name: Optional[str] = None) -> bool:
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
            display_name = name or f"Camera {cam_num} ({camera_id})"
            if not self.add_camera(camera_id, display_name, f"push_stream:{camera_id}"):
                # Another upload may have registered this device while this
                # request was waiting for the manager lock.
                with self.lock:
                    if camera_id not in self.workers:
                        return False
            print(f"[MultiCam] New push-stream device registered: {display_name} → {CAMERA_ZONES.get(camera_id, {}).get('label','?')}")

        with self.lock:
            if camera_id in self.workers:
                self.workers[camera_id].push_frame(frame)
                return True
        return False

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
        all_tracks_global: List[Dict] = []
        active_tracks_by_cam: Dict[str, List[int]] = {}
        camera_headcounts: Dict[str, int] = {}
        camera_avatar_counts: Dict[str, int] = {}

        with self.lock:
            workers_snapshot = list(self.workers.items())

        for cam_id, worker in workers_snapshot:
            _, contract = worker.get_latest_data()

            hc = contract.get("headcount", 0) if contract else 0
            camera_headcounts[cam_id] = hc
            c_risk = contract.get("risk_score_current", 0.0) if contract else 0.0
            max_risk = max(max_risk, c_risk)

            p_risk = contract.get("risk_score_predicted", {}) if contract else {}
            p_headcounts = contract.get("predicted_headcounts", {}) if contract else {}

            predicted_30s += p_headcounts.get("30s", hc)
            predicted_60s += p_headcounts.get("60s", hc)
            predicted_120s += p_headcounts.get("120s", hc)

            zone = worker.zone

            if contract:
                tracks = contract.get("tracks", [])
                tracks_by_id = {t.get("track_id"): t for t in tracks}
                # Build active local track IDs for global ID registry
                active_tracks_by_cam[cam_id] = [t["track_id"] for t in tracks if t.get("track_id", -1) > 0]

                # Collect tracks for cross-camera dedup (only between overlapping zones)
                for t in tracks:
                    all_tracks_global.append({
                        "camera_id": cam_id,
                        "track_id": t.get("track_id"),
                        "appearance": t.get("appearance", []),
                        "zone": zone,
                    })

                dt_state = contract.get("digital_twin_state", {})
                avatars = dt_state.get("avatars", [])
                camera_avatar_counts[cam_id] = len(avatars)
                for av in avatars:
                    # position_twin_xz is the display coordinate used by the mini-map.
                    xz = av.get("position_twin_xz", [50.0, 50.0])
                    norm_x = xz[0] / 100.0   # 0.0 – 1.0 within camera frame
                    norm_y = xz[1] / 100.0

                    av["camera_id"] = cam_id
                    av["zone"] = zone
                    track_info = tracks_by_id.get(av.get("avatar_id"), {})
                    av["local_track_id"] = av.get("avatar_id")
                    av["appearance"] = track_info.get("appearance", [])
                    av["twin_x"] = round(zone["x"] + min(max(norm_x, 0.0), 1.0) * zone["w"], 4)
                    av["twin_y"] = round(zone["y"] + min(max(norm_y, 0.0), 1.0) * zone["h"], 4)
                    vel = av.get("velocity_vector", [0.0, 0.0])
                    if len(vel) == 2:
                        av["velocity_vector"] = [round(vel[0] * zone["w"], 2), round(vel[1] * zone["h"], 2)]
                    all_avatars.append(av)

            camera_summaries.append({
                "camera_id": cam_id,
                "name": worker.name,
                "headcount": hc,
                "risk_current": c_risk,
                "risk_30s": p_risk.get("30s", 0.0),
                "zone": zone,
                "health": worker.get_health(),
            })

        # Update global ID pool — release IDs for people who left all cameras
        id_map = _global_id_registry.update(active_tracks_by_cam)
        # Remap avatar IDs to compact global IDs
        for av in all_avatars:
            cam_id = av.get("camera_id", "")
            local_id = av.get("avatar_id", -1)
            gid = id_map.get((cam_id, local_id), local_id)
            av["avatar_id"] = gid

        # Cross-camera Re-ID dedup — only between cameras whose zones actually overlap
        # Non-overlapping zones by definition cannot have the same person simultaneously
        authoritative_camera_id = "global_zone_fusion" if all_avatars else ""
        display_avatars = merge_duplicate_avatars(all_avatars)
        unique_headcount = len(display_avatars) if display_avatars else sum(c["headcount"] for c in camera_summaries)

        alerts = []
        predicted_peak = max(predicted_30s, predicted_60s, predicted_120s)
        if unique_headcount >= STAMPEDE_HEADCOUNT_THRESHOLD:
            alerts.append({
                "level": "CRITICAL",
                "message": "STAMPEDE_A"
            })
        elif predicted_peak >= STAMPEDE_HEADCOUNT_THRESHOLD:
            alerts.append({
                "level": "CRITICAL",
                "message": "STAMPEDE_A"
            })
        if max_risk > STAMPEDE_RISK_THRESHOLD:
            alerts.append({"level": "CRITICAL", "message": "STAMPEDE_A"})
        if predicted_120s > unique_headcount + STAMPEDE_PREDICTED_INCREASE and unique_headcount > 0:
            alerts.append({"level": "WARNING", "message": "STAMPEDE_A"})
        stampede_event = None
        if alerts:
            stampede_event = "STAMPEDE_A"

        return {
            "global_headcount": unique_headcount,
            "global_max_risk": round(max_risk, 2),
            "predicted_headcounts": {
                "30s": predicted_30s,
                "60s": predicted_60s,
                "120s": predicted_120s
            },
            "active_cameras_count": len(workers_snapshot),
            "maximum_cameras": MAX_CCTV_DEVICES,
            "twin_mode": "zone_based_global_floor",
            "headcount_mode": "zone_sum_with_overlap_reid",
            "authoritative_camera_id": authoritative_camera_id,
            "cameras": camera_summaries,
            "digital_twin_avatars": display_avatars,
            "alerts": alerts,
            "stampede_event": stampede_event,
            "camera_zones": CAMERA_ZONES
        }



    def stop_all(self):
        with self.lock:
            for worker in self.workers.values():
                worker.stop()
            self.workers.clear()

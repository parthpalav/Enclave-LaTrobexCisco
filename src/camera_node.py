"""
CrowdFlow Camera Node
=====================
Streams any camera source to the Central Dashboard Server.

Supported Sources:
  --source 0            → Laptop/USB webcam (index)
  --source rtsp://...   → RTSP IP camera or phone streaming app
  --source http://...   → HTTP MJPEG stream (IP Webcam Android app, DroidCam, etc.)

Phone Setup (No App Required — Web Browser):
  Open  http://<HOST_IP>:<PORT>/phone  on the phone browser.
  The dashboard server serves a browser-based capture page that uses the
  phone's rear camera via WebRTC getUserMedia and POSTs frames via fetch().

Phone Setup (IP Webcam Android App — Most Reliable):
  1. Install "IP Webcam" from Play Store (free).
  2. Tap "Start Server" → note the IP shown (e.g. http://192.168.1.20:8080).
  3. On this laptop run:
     python src/camera_node.py --server http://<HOST_IP>:5000 --source http://192.168.1.20:8080/video --id phone_1

iPhone (EpocCam / Camo):
  Install EpocCam or Camo → exposes RTSP or USB source.
"""

import cv2
import argparse
import time
import requests
import socket
import threading
import sys
import warnings

# Suppress SSL warnings from self-signed server certificate (expected on LAN)
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_default_node_id():
    try:
        return f"cam_{socket.gethostname().replace('-', '_').replace(' ', '_')}"
    except Exception:
        return "cam_node"

def is_http_mjpeg(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")

def is_rtsp(source: str) -> bool:
    return source.startswith("rtsp://") or source.startswith("rtsps://")

# ──────────────────────────────────────────────
# Frame sender thread (non-blocking upload)
# ──────────────────────────────────────────────

class FrameSender(threading.Thread):
    """
    Sends JPEG frames to the central server in a background thread,
    so camera capture is never blocked by slow network.
    """
    def __init__(self, server_url: str, cam_id: str, fps: int):
        super().__init__(daemon=True)
        self.server_url = server_url
        self.cam_id = cam_id
        self.frame_delay = 1.0 / max(1, fps)
        self._pending = None
        self._lock = threading.Lock()
        self._running = True
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})
        self._consecutive_errors = 0

    def push(self, jpeg_bytes: bytes):
        """Called from capture thread to stage the latest frame."""
        with self._lock:
            self._pending = jpeg_bytes

    def run(self):
        while self._running:
            t0 = time.time()
            with self._lock:
                frame_bytes = self._pending
                self._pending = None

            if frame_bytes is not None:
                try:
                    self.session.post(
                        self.server_url,
                        files={"frame": ("frame.jpg", frame_bytes, "image/jpeg")},
                        data={"camera_id": self.cam_id},
                        timeout=5.0,
                        verify=False
                    )
                    self._consecutive_errors = 0
                except Exception:
                    self._consecutive_errors += 1
                    backoff = min(3.0, 0.2 * self._consecutive_errors)
                    print(f"[CameraNode] Network error (attempt {self._consecutive_errors}), retrying in {backoff:.1f}s...")
                    time.sleep(backoff)

            elapsed = time.time() - t0
            sleep_rem = self.frame_delay - elapsed
            if sleep_rem > 0:
                time.sleep(sleep_rem)

    def stop(self):
        self._running = False


# ──────────────────────────────────────────────
# Heartbeat thread — tells server node is alive
# ──────────────────────────────────────────────

class HeartbeatThread(threading.Thread):
    def __init__(self, base_url: str, cam_id: str):
        super().__init__(daemon=True)
        self.url = base_url.rstrip("/") + "/api/heartbeat"
        self.cam_id = cam_id
        self._running = True

    def run(self):
        s = requests.Session()
        while self._running:
            try:
                s.post(self.url, json={"camera_id": self.cam_id}, timeout=3.0)
            except Exception:
                pass
            time.sleep(5)

    def stop(self):
        self._running = False


# ──────────────────────────────────────────────
# Open video source with auto-retry
# ──────────────────────────────────────────────

def open_source(source) -> cv2.VideoCapture:
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
    return cap


# ──────────────────────────────────────────────
# Main capture loop
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CrowdFlow Camera Node — Stream any camera to the Central Dashboard")
    parser.add_argument("--server",  type=str, default="http://localhost:5000",
                        help="Central dashboard URL  (e.g. http://192.168.1.15:8080)")
    parser.add_argument("--source",  type=str, default="0",
                        help="Camera source: 0=webcam, rtsp://..., http://phone_ip:8080/video")
    parser.add_argument("--fps",     type=int, default=15,
                        help="Target streaming FPS (default 15)")
    parser.add_argument("--quality", type=int, default=70,
                        help="JPEG quality 1-100 (default 70, lower = faster)")
    parser.add_argument("--id",      type=str, default=None,
                        help="Custom camera ID (default: hostname-based)")
    parser.add_argument("--flip",    action="store_true",
                        help="Flip frame horizontally (mirror mode)")
    args = parser.parse_args()

    cam_id = args.id or get_default_node_id()
    server_url = args.server.rstrip("/") + "/api/stream_upload"

    print("=" * 55)
    print("  CrowdFlow Camera Node")
    print(f"  Camera ID  : {cam_id}")
    print(f"  Source     : {args.source}")
    print(f"  Server     : {server_url}")
    print(f"  Target FPS : {args.fps}  |  JPEG Quality: {args.quality}")
    print("=" * 55)

    # Verify server reachable
    try:
        r = requests.get(args.server.rstrip("/") + "/api/analytics", timeout=5, verify=False)
        print(f"[CameraNode] ✓ Server reachable ({r.status_code})")
    except Exception as e:
        print(f"[CameraNode] ✗ Cannot reach server: {e}")
        print("[CameraNode] Make sure:")
        print("  1. Dashboard server is running on the host laptop")
        print("  2. Windows Firewall allows the port (run as Admin):")
        print(f"     New-NetFirewallRule -DisplayName CrowdFlow -Direction Inbound -Protocol TCP -LocalPort <PORT> -Action Allow")
        sys.exit(1)

    # Start background sender & heartbeat
    sender = FrameSender(server_url, cam_id, fps=args.fps)
    sender.start()

    heartbeat = HeartbeatThread(args.server, cam_id)
    heartbeat.start()

    print(f"[CameraNode] Streaming live feed to {server_url} ...")
    print("[CameraNode] Press Ctrl+C to stop.\n")

    source = args.source
    cap = None
    consecutive_fails = 0
    MAX_FAILS = 30

    try:
        while True:
            # (Re-)open source
            if cap is None or not cap.isOpened():
                print(f"[CameraNode] Opening source: {source}")
                cap = open_source(source)
                if not cap.isOpened():
                    print(f"[CameraNode] Could not open {source}. Retrying in 3s...")
                    time.sleep(3)
                    continue
                consecutive_fails = 0

            ret, frame = cap.read()

            if not ret:
                consecutive_fails += 1
                if consecutive_fails >= MAX_FAILS:
                    print(f"[CameraNode] Lost stream ({consecutive_fails} consecutive failures). Reopening...")
                    cap.release()
                    cap = None
                    consecutive_fails = 0
                    time.sleep(1)
                continue

            consecutive_fails = 0

            if args.flip:
                frame = cv2.flip(frame, 1)

            # Resize for network efficiency
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))

            ok, jpeg = cv2.imencode(
                ".jpg", frame,
                [cv2.IMWRITE_JPEG_QUALITY, args.quality]
            )
            if ok:
                sender.push(jpeg.tobytes())

    except KeyboardInterrupt:
        print("\n[CameraNode] Stopped by user.")
    finally:
        sender.stop()
        heartbeat.stop()
        if cap is not None:
            cap.release()


if __name__ == "__main__":
    main()

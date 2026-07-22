import os
import time
import cv2
import argparse
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
from multi_camera_manager import MultiCameraManager

app = Flask(__name__, template_folder="templates")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yaml")
camera_manager = MultiCameraManager(config_path)

def generate_camera_stream(camera_id: str):
    """
    MJPEG live stream generator for specified camera_id.
    """
    while True:
        if camera_id in camera_manager.workers:
            worker = camera_manager.workers[camera_id]
            frame, _ = worker.get_latest_data()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect_camera')
def connect_camera():
    return render_template('connect_camera.html')

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    return Response(generate_camera_stream(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stream_upload', methods=['POST'])
def stream_upload():
    """
    Instant non-blocking stream upload receiver (<2ms response time).
    Prevents client read timeouts on secondary laptops.
    """
    if 'frame' not in request.files:
        return jsonify({"error": "no frame"}), 400

    camera_id = request.form.get('camera_id', 'laptop_2')
    file = request.files['frame']
    img_bytes = file.read()

    # Fast numpy decode
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is not None:
        camera_manager.push_laptop_frame(camera_id, frame)
        return jsonify({"success": True, "camera_id": camera_id}), 200

    return jsonify({"error": "invalid image"}), 400

@app.route('/api/analytics')
def get_analytics():
    data = camera_manager.get_global_analytics()
    return jsonify(data)

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Lightweight endpoint: camera nodes ping this every 5s to confirm they are alive."""
    data = request.get_json() or {}
    cam_id = data.get("camera_id", "unknown")
    if cam_id in camera_manager.workers:
        camera_manager.workers[cam_id].last_heartbeat = time.time()
    return jsonify({"ok": True}), 200

@app.route('/phone')
def phone_capture():
    """Browser-based camera capture page — open on phone browser over LAN."""
    return render_template('phone_capture.html')

@app.route('/api/add_camera', methods=['POST'])
def add_camera():
    req = request.get_json() or {}
    cam_id = req.get("camera_id", f"cam_{len(camera_manager.workers) + 1}")
    name = req.get("name", f"Camera {len(camera_manager.workers) + 1}")
    source = req.get("source", "0")

    success = camera_manager.add_camera(cam_id, name, source)
    return jsonify({"success": success, "camera_id": cam_id, "name": name, "source": source})

def main():
    parser = argparse.ArgumentParser(description="Central Digital Twin Control Room Dashboard Server")
    parser.add_argument("--port",  type=int, default=5000, help="Web dashboard HTTP port (default 5000)")
    parser.add_argument("--host",  type=str, default="0.0.0.0", help="Host IP address to bind (0.0.0.0 for LAN)")
    parser.add_argument("--https", action="store_true", help="Enable HTTPS (required for phone camera access via browser)")
    args = parser.parse_args()

    proto = "https" if args.https else "http"
    print(f"==========================================================")
    print(f"  Central Digital Twin & Crowd Prediction Dashboard       ")
    print(f"  Dashboard : {proto}://localhost:{args.port}              ")
    print(f"  Phone Cam : {proto}://192.168.1.15:{args.port}/phone     ")
    print(f"==========================================================")
    if args.https:
        print("  [HTTPS] Phone will show 'Not Secure' warning — tap Advanced → Proceed")
        print(f"==========================================================")

    # Initialize ONLY real active physical cameras (Camera 1)
    camera_manager.add_camera("cam_1", "Camera 1 (Main Webcam)", 0)

    ssl_context = 'adhoc' if args.https else None
    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True, ssl_context=ssl_context)
    finally:
        camera_manager.stop_all()

if __name__ == "__main__":
    main()

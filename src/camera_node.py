import cv2
import argparse
import time
import requests
import socket

def get_laptop_name():
    try:
        return socket.gethostname()
    except Exception:
        return "Secondary_Laptop"

def main():
    parser = argparse.ArgumentParser(description="Secondary Laptop Camera Streamer Node")
    parser.add_argument("--server", type=str, default="http://localhost:5000", help="Central dashboard server URL (e.g., http://192.168.1.15:5000)")
    parser.add_argument("--source", type=int, default=0, help="Camera index (default 0 for built-in webcam)")
    parser.add_argument("--fps", type=int, default=12, help="Streaming target FPS (default 12)")
    args = parser.parse_args()

    server_url = args.server.rstrip('/') + '/api/stream_upload'
    cam_id = f"cam_{get_laptop_name().replace('-', '_')}"

    print(f"==================================================")
    print(f"  Secondary Laptop Camera Node Starting           ")
    print(f"  Camera ID:  {cam_id}                            ")
    print(f"  Target Server: {server_url}                      ")
    print(f"==================================================")

    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        print(f"[CameraNode] Error: Could not open camera source {args.source}")
        return

    frame_delay = 1.0 / max(1, args.fps)
    print(f"[CameraNode] Streaming live webcam feed to central server...")

    session = requests.Session()

    while True:
        start_t = time.time()
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        # Resize to 640x480 for fast transmission
        frame_resized = cv2.resize(frame, (640, 480))
        ret, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ret:
            continue

        try:
            files = {'frame': ('frame.jpg', buffer.tobytes(), 'image/jpeg')}
            data = {'camera_id': cam_id}
            # Timeout set to 5.0 seconds with persistent HTTP session
            session.post(server_url, files=files, data=data, timeout=5.0)
        except Exception as e:
            print(f"[CameraNode] Notice: Network sync delay... retrying")
            time.sleep(0.5)

        elapsed = time.time() - start_t
        if elapsed < frame_delay:
            time.sleep(frame_delay - elapsed)

    cap.release()

if __name__ == "__main__":
    main()

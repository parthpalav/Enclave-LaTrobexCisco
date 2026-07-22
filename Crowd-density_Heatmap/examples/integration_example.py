"""Minimal example of integrating CrowdVision from another service.

Shows the entire integration surface the main platform needs:
    1. add a camera
    2. poll current analytics
    3. fetch the latest heatmap image

Run the engine first (docker compose or uvicorn), then:
    python examples/integration_example.py --source path/to/video.mp4
"""

from __future__ import annotations

import argparse
import base64
import time

import httpx

BASE = "http://localhost:8000/api/v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="RTSP URL, file path or webcam index")
    parser.add_argument("--camera-id", default="demo-cam")
    parser.add_argument("--base", default=BASE)
    args = parser.parse_args()

    with httpx.Client(base_url=args.base, timeout=30) as client:
        # 1. Register + start the camera.
        r = client.post(
            "/camera/add",
            json={"camera_id": args.camera_id, "name": "Demo", "source": args.source},
        )
        r.raise_for_status()
        print("Camera started:", r.json())

        # 2. Poll analytics for a few seconds.
        for _ in range(10):
            time.sleep(1.0)
            try:
                a = client.get("/analytics/current", params={"camera_id": args.camera_id})
                if a.status_code == 200:
                    d = a.json()
                    print(
                        f"people={d['people_count']:>3}  "
                        f"score={d['density_score']:>5}  "
                        f"max_density={d['max_density']:.2f}  fps={d.get('fps')}"
                    )
            except httpx.HTTPError as exc:
                print("waiting for frames…", exc)

        # 3. Save the latest heatmap image.
        h = client.get("/heatmap/latest", params={"camera_id": args.camera_id})
        if h.status_code == 200:
            data = h.json()["image"].split(",", 1)[1]
            with open("latest_heatmap.jpg", "wb") as f:
                f.write(base64.b64decode(data))
            print("Saved latest_heatmap.jpg")


if __name__ == "__main__":
    main()

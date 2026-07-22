import os
import sys
import argparse
import json
import cv2
import time
from config import load_config
from pipeline import CrowdFlowPipeline
from test_data_generator import generate_synthetic_crowd_video

def main():
    parser = argparse.ArgumentParser(description="Crowd Detection, Tracking & Flow Prediction Pipeline")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml file")
    parser.add_argument("--source", type=str, default=None, help="Video file path or camera index (e.g. 0)")
    parser.add_argument("--webcam", action="store_true", help="Use live webcam feed (index 0)")
    parser.add_argument("--mirror", action="store_true", default=None, help="Mirror (flip horizontal) webcam feed")
    parser.add_argument("--no-mirror", action="store_false", dest="mirror", help="Disable mirror view")
    parser.add_argument("--backend", type=str, default=None, choices=["raft_small", "farneback"], help="Optical flow backend")
    parser.add_argument("--no-arrows", action="store_true", help="Hide optical flow vector arrows")
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI visualization window")
    parser.add_argument("--max-frames", type=int, default=0, help="Max frames to process (0 = process all)")
    parser.add_argument("--save-json", type=str, default=None, help="File path to log output JSON contract per frame")
    args = parser.parse_args()

    # Load configuration
    cfg = load_config(args.config)
    is_webcam = False

    if args.webcam:
        cfg.input_source = "0"
        is_webcam = True
    elif args.source:
        cfg.input_source = args.source
        if str(args.source).isdigit():
            is_webcam = True

    # Default mirror view to True for webcam feeds unless explicitly --no-mirror
    if args.mirror is None:
        mirror_view = is_webcam
    else:
        mirror_view = args.mirror

    if args.backend:
        cfg.optical_flow.backend = args.backend
    if args.no_gui:
        cfg.visualization.show_gui = False
    if args.no_arrows:
        cfg.visualization.draw_flow_arrows = False

    # Check input video source
    source = cfg.input_source
    if str(source).isdigit():
        video_cap_source = int(source)
    else:
        video_cap_source = source
        if not os.path.exists(source) and not str(source).startswith("rtsp://") and not str(source).startswith("http"):
            print(f"[Main] Input video source '{source}' not found. Generating synthetic crowd test video...")
            generate_synthetic_crowd_video(output_path=source, duration_sec=15, fps=int(cfg.target_fps))

    print(f"[Main] Opening video input source: {video_cap_source} (Mirror View: {mirror_view})")
    cap = cv2.VideoCapture(video_cap_source)
    if not cap.isOpened():
        print(f"[Main] Error: Could not open video source '{video_cap_source}'. Exiting.")
        sys.exit(1)

    # Instantiate Pipeline
    pipeline = CrowdFlowPipeline(cfg)

    json_file = None
    if args.save_json:
        json_file = open(args.save_json, "w", encoding="utf-8")

    frame_count = 0
    start_time = time.time()

    print("[Main] Starting pipeline execution... Press 'q' or ESC in display window to stop.")
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("[Main] End of video stream or error reading frame.")
                break

            # Apply horizontal mirror flip for natural webcam view
            if mirror_view:
                frame = cv2.flip(frame, 1)

            frame_count += 1
            if args.max_frames > 0 and frame_count > args.max_frames:
                print(f"[Main] Reached max frames limit ({args.max_frames}). Stopping.")
                break

            # Execute pipeline on current frame
            contract_output, rendered_frame = pipeline.process_frame(frame)

            # Print or log output contract
            if json_file:
                json_file.write(json.dumps(contract_output) + "\n")
            elif frame_count % 10 == 0:
                print(f"[Frame {frame_count}] Headcount: {contract_output['headcount']} | Current Risk: {contract_output['risk_score_current']} | Predicted 30s: {contract_output['risk_score_predicted'].get('30s')}")

            # Display GUI window
            if cfg.visualization.show_gui:
                cv2.imshow("Crowd Detection, Tracking & Flow Prediction Pipeline", rendered_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("[Main] User interrupt requested (q/ESC). Exiting loop.")
                    break

    except KeyboardInterrupt:
        print("[Main] KeyboardInterrupt received. Exiting...")
    finally:
        elapsed = time.time() - start_time
        avg_fps = frame_count / max(elapsed, 1e-4)
        print(f"[Main] Processed {frame_count} frames in {elapsed:.2f}s (Average FPS: {avg_fps:.2f})")

        cap.release()
        if cfg.visualization.show_gui:
            cv2.destroyAllWindows()
        if json_file:
            json_file.close()
            print(f"[Main] Output contract JSON saved to '{args.save_json}'.")

if __name__ == "__main__":
    main()

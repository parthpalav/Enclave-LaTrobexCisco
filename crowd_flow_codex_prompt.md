# Build Prompt for Codex: Crowd Detection, Tracking & Flow Prediction

## Goal
Build a real-time pipeline that takes a single video feed (file or stream) of a crowd and produces:
1. Person detection + tracking (headcount, positions, track IDs)
2. Dense optical flow (direction/speed field of crowd motion)
3. Divergence of the flow field (convergence / stampede-risk detection)
4. Advection-based prediction of crowd density 30s / 60s / 120s into the future

No 360° handling, no routing, no alerting — just this perception + prediction pipeline. Target hardware: NVIDIA RTX 4050, 6GB VRAM. Everything must run in real time on this GPU.

---

## Step 1 — Detection + Tracking
- Use **YOLOv8** (`yolov8s` to start) for person detection, class-filtered to `person` only, running on GPU.
- Feed detections into **ByteTrack** for persistent track IDs across frames.
- Run detection every frame if benchmarks allow; make the cadence (every Nth frame) a config parameter in case full-frame-rate detection doesn't hit the real-time budget.
- Per-frame output: list of `{track_id, bbox, center_xy, confidence}`.
- Derive **headcount** as a direct byproduct (count of active detections that frame).
- Log per-frame inference time for this stage.

## Step 2 — Dense Optical Flow
- Compute dense optical flow on **downsampled** frames (start at ~320×240, tune up/down based on benchmark — flow doesn't need full resolution, crowd-direction accuracy only needs to be regional, not pixel-level).
- Implement as a swappable backend behind one interface, with two implementations:
  - **RAFT-small** on GPU (primary — VRAM budget allows it)
  - **OpenCV CUDA Farneback** (fallback/baseline for comparison and as a safety net if RAFT integration takes too long)
- Bin the raw flow output into a coarse grid (e.g. 20×20 or 30×30 cells) covering the frame — don't pass per-pixel flow downstream, aggregate it into per-cell average vectors.
- Per-frame output: grid of `(dx, dy)` vectors, one per cell.
- Log per-frame compute time for this stage separately from detection.

## Step 3 — Divergence / Risk Signal
- Compute discrete **divergence** of the binned flow field (standard finite-difference divergence: net outflow per cell relative to neighbors).
- Negative divergence = vectors converging into a cell = stampede-risk signal. Flag cells crossing a configurable negative threshold.
- Also compute a simple **density** value (headcount from Step 1 relative to frame/zone area) and a basic **counter-flow** signal (opposing vector directions within a local region) — keep these as separate, inspectable values, not folded silently into one number.
- Combine into a single **risk score** as a weighted sum (`risk = a*density + b*|negative_divergence| + c*counterflow`). Make `a`, `b`, `c` and the divergence threshold config values, not hardcoded — they'll need calibration against real footage.
- Output a risk score + the raw divergence map per frame.

## Step 4 — Advection-Based Prediction
- Implement **advection**: push the current density map forward along the current flow vector field to estimate density at future timestamps.
- Use semi-Lagrangian advection (sample backward along flow vectors to interpolate the predicted future state) — this is a physics computation, not a trained model, and needs zero training data.
- Correctly convert the requested horizons (**30s, 60s, 120s**) into frame/timestep counts using the pipeline's actual measured FPS, not an assumed constant.
- Recompute the Step 3 risk signals (divergence, density, counter-flow, risk score) on each predicted future state, producing a **predicted risk score per horizon**.
- Output: predicted density maps + predicted risk scores for 30s/60s/120s ahead.

## Output contract (per processed frame)
Emit a single structured object per frame/tick so this pipeline has a clean boundary for whatever consumes it later (routing, dashboard, alerts — not part of this task):
```json
{
  "timestamp": ...,
  "headcount": int,
  "tracks": [{"track_id": int, "bbox": [...], "center_xy": [...]}],
  "flow_field": [[dx, dy], ...],
  "divergence_map": [[...]],
  "risk_score_current": float,
  "risk_score_predicted": {"30s": float, "60s": float, "120s": float}
}
```

## Non-functional requirements
- **Real-time target**: define a target FPS as a config constant (e.g. 15–20 FPS end-to-end) and log per-stage timing (detection, tracking, flow, divergence, advection) separately so bottlenecks are visible immediately, not guessed at.
- **VRAM budget**: YOLOv8s + RAFT-small must fit comfortably in 6GB together — note expected VRAM usage in comments.
- **Config-driven**: model choice (RAFT vs Farneback), detection cadence, flow grid size, risk weights, thresholds, and prediction horizons should all live in one config file, not scattered as magic numbers.
- **Debug visualization**: render an overlay per frame — bounding boxes with track IDs, flow vectors as arrows, divergence as a heatmap — this is how you'll sanity-check each stage as it's built, and doubles as the demo visual later.
- Build against a **local video file** first, but don't hardcode file-based assumptions deep in the logic — keep the input source swappable for a live camera stream later.

## Suggested build order (implement + validate each before moving on)
1. `detect_track.py` — YOLOv8 + ByteTrack, validate against the debug overlay (correct boxes, stable track IDs)
2. `optical_flow.py` — flow backend interface + RAFT-small/Farneback implementations, validate flow arrows look physically sensible on real footage
3. `risk_signals.py` — divergence/density/counter-flow/risk score, validate divergence heatmap lights up at known convergence points in your test footage
4. `prediction.py` — advection forward-projection, validate predicted density map visually resembles where the crowd actually ends up N seconds later (compare against real future frames from the same video)
5. `pipeline.py` — orchestrates all stages per frame, emits the output contract, includes per-stage timing/logging
6. `visualize.py` — the debug overlay renderer used throughout

Implement and test each module independently before wiring the next one in — don't build the full pipeline end-to-end before any single stage has been validated on real footage.

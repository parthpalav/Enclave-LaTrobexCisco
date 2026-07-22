# Architecture

## 1. Position in the larger platform

CrowdVision is one **independent** microservice. It never contains GIS / Google
Earth Engine logic — that belongs to the main platform, which *consumes* this
engine's APIs.

```
                 Smart Disaster Management Platform
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
 CrowdVision Engine     Indoor Navigation      Alert Engine
 (this module)          (future)               (future)
        │
        ▼
 REST API + WebSocket
        │
        ▼
   Main Backend (FastAPI)
        │
        ▼
 Google Earth Engine + Outdoor Maps + GIS
```

Why split it out:

- **Reusable** — deployable on its own (GitHub / Docker / cloud).
- **Decoupled** — the platform only speaks HTTP; AI internals can change freely.
- **Scalable** — run N heatmap engines (one per site) behind the platform.

## 2. Processing pipeline (per camera)

```
 RTSP/File ─► VideoCapture ─► resize(720p)
      ─► YOLOv11.track()  ────────────► detections + ByteTrack IDs
      ─► MovementTracker  ────────────► per-person velocity/speed
      ─► DensityEstimator ────────────► Gaussian KDE density field [0..1]
      ─► AnalyticsComputer ───────────► counts, scores, crowded zones
      ─► HeatmapGenerator ────────────► colour-mapped, alpha-blended overlay
      ─► JPEG encode ─────────────────► published latest frame + analytics
```

Each camera runs in its **own daemon thread** (blocking CV/AI work) and
publishes the latest JPEG + analytics behind a lock. The async FastAPI layer
reads that published state without blocking the event loop — so many cameras and
many WebSocket clients coexist.

An async **persistence loop** samples published analytics at a fixed cadence
(`ANALYTICS_PERSIST_INTERVAL`) and writes to PostgreSQL + Redis, decoupling DB
writes from frame processing.

## 3. Module responsibilities (SOLID)

| Layer | Module | Single responsibility |
|-------|--------|-----------------------|
| core | `config`/`settings` | Typed configuration from env (no hardcoding) |
| core | `logger` | Structured/plain logging |
| models | `yolo_detector` | YOLO load + detect/track (ByteTrack) |
| models | `tracker` | Movement analytics from track IDs |
| models | `gaussian` | Gaussian kernel + additive splatting |
| models | `density` | KDE density field (downscale → filter → upscale) |
| models | `heatmap` | Colour-map + per-pixel alpha blend |
| services | `analytics_service` | Per-frame statistics + crowded zones |
| services | `stream_service` | Per-camera pipeline thread + published state |
| services | `camera_service` | Pipeline lifecycle manager (singleton) |
| services | `storage_service` | Persistence + Redis cache + alerts |
| database | `models`/`schemas`/`session` | ORM, Pydantic contract, async engine |
| api | `camera`/`analytics`/`stream`/`health` | Thin HTTP/WS controllers |

Dependency injection is via FastAPI `Depends` and swappable singletons
(`get_camera_manager`, `get_storage_service`, `get_settings`).

## 4. Heatmap algorithm (why it's smooth, not blocky)

1. For each person take the **foot point** (bottom-centre of the box) — the
   ground contact, which is more physically meaningful than the head/centre.
2. Splat unit impulses onto a **downscaled** canvas (speed).
3. Apply a **Gaussian filter** (SciPy) with configurable `sigma` — this *is* the
   kernel-density estimate; overlapping kernels add up continuously.
4. Upsample (bilinear) to full resolution and **normalise** with a temporally
   smoothed running max (prevents flicker).
5. Map density → colour with the CrowdVision ramp
   (blue→green→yellow→orange→red).
6. **Per-pixel alpha**: 0 below `HEATMAP_MIN_DENSITY`, ramping to `HEATMAP_ALPHA`
   at peak — so sparse areas stay fully transparent and the overlay *fades*
   instead of drawing rectangles.

Kernel `sigma` and size are fully configurable via env.

## 5. Data model

- **Camera** — metadata (id, name, source, location, lat/lng).
- **FrameAnalytics** — the sampled per-frame stats (the only high-volume table).
- **HeatmapHistory** — optional downscaled heatmap snapshots (analytics artefact,
  not raw video).
- **Alert** — threshold breaches (people / density).

> **Raw CCTV video is never persisted** unless `STORE_RAW_VIDEO=true`. A live raw
> preview is kept in memory only, for the dashboard.

## 6. Performance & scaling

- Target: 720p @ ~25 FPS, sub-200 ms latency with a GPU (`yolo11n`).
- Density computed at `HEATMAP_DOWNSCALE` (default 0.5) for speed.
- CPU fallback works (lower FPS); GPU via CUDA torch + NVIDIA runtime.
- Horizontal scale: run multiple engine instances; the platform load-balances by
  camera. State is per-instance; Postgres/Redis are shared.

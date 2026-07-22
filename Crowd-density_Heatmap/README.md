# CrowdVision — AI-Powered Crowd Heatmap Engine

A production-ready, modular **microservice** that ingests live CCTV/IP-camera
streams (or uploaded videos), detects people in real time, estimates crowd
density, and renders a smooth Gaussian heatmap overlaid on the original frame.

Built to run **independently** and be consumed by a larger platform (e.g. a
Smart Disaster Management System) purely through **REST + WebSocket APIs** — the
consuming system never needs to know how the AI works internally.

```
RTSP/IP camera ─► Frame capture ─► YOLOv11 detection ─► ByteTrack tracking
      ─► Gaussian KDE density ─► Heatmap generation ─► Overlay ─► Live stream
```

---

## ✨ Features

- **Detection** — YOLOv11 (auto-fallback to YOLOv8), person class only.
- **Tracking** — ByteTrack, isolated state per camera.
- **Density** — Gaussian **Kernel Density Estimation** (smooth, *no grids*).
- **Heatmap** — semi-transparent overlay, blue → green → yellow → orange → red,
  smoothly fading to transparent where the scene is sparse.
- **Analytics** — people count, density score, avg/max density, crowded zones,
  movement index, timestamp — persisted to PostgreSQL.
- **Streaming** — MJPEG + WebSocket live output.
- **APIs** — clean REST surface + WebSocket for integration.
- **Dashboard** — React + Vite + TypeScript + Tailwind (original camera,
  heatmap, live analytics, status).
- **Deployment** — Docker, Docker Compose, GitHub Actions, health checks, env
  config, CPU/GPU (CUDA) support.

---

## 🗂 Project structure

```
crowdvision-heatmap/
├── backend/          FastAPI service (AI pipeline, APIs, DB)
│   ├── app/
│   │   ├── api/          camera · analytics · stream · health
│   │   ├── core/         config · settings · logger
│   │   ├── models/       yolo_detector · tracker · density · gaussian · heatmap
│   │   ├── services/     camera · analytics · stream · storage
│   │   ├── database/     models · schemas · session
│   │   ├── utils/        image · color · math
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/         React + Vite + TS + Tailwind dashboard
├── docker/           Dockerfiles + docker-compose.yml
├── docs/             API · Architecture · Deployment
└── .github/workflows/ci.yml
```

---

## 🚀 Quick start

### Option A — Docker Compose (everything, one command)

```bash
docker compose -f docker/docker-compose.yml up --build
```

- Dashboard → http://localhost:8080
- API docs (Swagger) → http://localhost:8000/docs
- Health → http://localhost:8000/api/v1/health

### Option B — Local dev

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit as needed
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 (proxies to :8000)
```

### Add your first camera

```bash
curl -X POST http://localhost:8000/api/v1/camera/add \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"cam-01","name":"Main Gate","source":"rtsp://user:pass@192.168.1.10:554/stream1"}'
```

`source` can be an **RTSP/HTTP URL**, a **video file path**, or a **webcam index**
(e.g. `"0"`). Open the dashboard, select the camera, watch the heatmap.

---

## 🔌 API summary

| Method | Path                     | Purpose                        |
|--------|--------------------------|--------------------------------|
| POST   | `/api/v1/camera/add`     | Register + start a camera      |
| POST   | `/api/v1/camera/remove`  | Stop + remove a camera         |
| GET    | `/api/v1/camera/list`    | List cameras + live status     |
| GET    | `/api/v1/analytics/current` | Latest analytics for a camera |
| GET    | `/api/v1/analytics/history` | Historical analytics        |
| GET    | `/api/v1/analytics/alerts`  | Recent crowd alerts         |
| GET    | `/api/v1/heatmap/latest` | Latest heatmap (base64 JPEG)   |
| GET    | `/api/v1/stream/mjpeg`   | MJPEG stream (overlay/raw)     |
| WS     | `/api/v1/stream/live`    | Live analytics + heatmap frames|
| GET    | `/api/v1/health`         | Health / readiness             |

Full contract with payloads in [`docs/API.md`](docs/API.md).

---

## 🧩 Integration (for the Disaster Management platform)

The engine is a black box behind HTTP. To integrate:

1. `POST /camera/add` with the camera source.
2. Consume `WS /stream/live` (or `/heatmap/latest`) for the live heatmap.
3. Consume `/analytics/current` + `/analytics/history` for metrics.

> **Architecture note:** keep Google Earth Engine / GIS *out* of this module.
> Run CrowdVision as its own service; let the main backend combine its APIs with
> GEE, outdoor maps, assembly points and flood/fire layers. See
> [`docs/Architecture.md`](docs/Architecture.md).

---

## 🔑 What YOU must provide (not included in this repo)

Nothing here needs a paid API key — YOLO/Ultralytics runs locally. But **you**
supply the following:

| Item | Needed for | Notes |
|------|-----------|-------|
| **Camera source URL(s)** | Real input | RTSP/HTTP from your CCTV/IP cameras, or a test `.mp4`. Not shipped. |
| **PostgreSQL credentials** | Analytics storage | Set `DATABASE_URL` in `.env`. Compose spins one up automatically. |
| **Redis** (optional) | Latest-analytics cache | `REDIS_URL`. Compose provides one; app runs without it. |
| **YOLO weights** | Detection | Auto-downloaded by Ultralytics on first run (needs internet once). To run fully offline, pre-download `yolo11n.pt`/`yolov8n.pt` and mount them. |
| **GPU + CUDA drivers** (optional) | 25 FPS @ 720p | For GPU install a CUDA `torch` wheel + NVIDIA Container Toolkit. CPU works but slower. |
| **`.env` file** | All config | Copy `backend/.env.example` → `backend/.env` and fill values. |
| **Your camera's real coordinates** | Map placement (later) | `latitude`/`longitude` on `camera/add` if you plan to map cameras. |

There are **no third-party API keys** (no Google Maps, no cloud vision API)
required for the engine itself. If you later add GEE in the *main* platform,
that key lives there, not here.

---

## 🧪 Testing

```bash
cd backend && pytest -q
```

Pure-pipeline tests (Gaussian, density, heatmap, analytics, API) run without a
GPU or model download. Detection tests self-skip when weights are unavailable.

---

## 📚 Docs

- [API reference](docs/API.md)
- [Architecture](docs/Architecture.md)
- [Deployment](docs/Deployment.md)

## License

MIT — see below. Provided for educational / capstone / research use.

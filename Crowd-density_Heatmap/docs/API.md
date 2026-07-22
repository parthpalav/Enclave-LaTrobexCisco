# API Reference

Base URL: `http://<host>:8000/api/v1`
Interactive docs (Swagger UI): `http://<host>:8000/docs`
OpenAPI JSON: `http://<host>:8000/openapi.json`

All request/response bodies are JSON unless noted. Timestamps are UNIX epoch
seconds (analytics payloads) or ISO-8601 (DB-backed history).

---

## Health

### `GET /health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "device": "cuda:0",
  "cameras_active": 2,
  "uptime_seconds": 1284.3
}
```

---

## Camera

### `POST /camera/add`

Register a camera and start its real-time pipeline.

**Body**

```json
{
  "camera_id": "cam-01",
  "name": "Main Gate",
  "source": "rtsp://user:pass@192.168.1.10:554/stream1",
  "location": "North Entrance",
  "latitude": 19.0760,
  "longitude": 72.8777,
  "enabled": true
}
```

`source` accepts an RTSP/HTTP URL, a local video file path, or a webcam index
(`"0"`).

**201 Response** — `CameraStatus`

```json
{
  "camera_id": "cam-01",
  "running": true,
  "connected": false,
  "fps": 0.0,
  "people_count": 0,
  "last_frame_at": null
}
```

`409` if the configured `MAX_CAMERAS` limit is reached.

### `POST /camera/remove`

```json
{ "camera_id": "cam-01" }
```

**200** → `{ "status": "removed", "camera_id": "cam-01" }` · `404` if unknown.

### `GET /camera/list`

Returns `CameraStatus[]` for all active pipelines.

---

## Analytics

### `GET /analytics/current?camera_id=cam-01`

Latest live analytics (in-memory, falls back to Redis cache).

```json
{
  "camera_id": "cam-01",
  "timestamp": 1721650000.42,
  "people_count": 37,
  "density_score": 61.4,
  "average_density": 0.083,
  "max_density": 0.74,
  "crowded_zones": [
    { "x": 640.0, "y": 380.0, "radius": 55.2, "intensity": 0.81 }
  ],
  "movement_index": 3.2,
  "fps": 24.6
}
```

`404` if no analytics exist yet for the camera.

### `GET /analytics/history?camera_id=cam-01&minutes=30&limit=500`

Historical analytics (most recent first) from PostgreSQL. Returns
`AnalyticsOut[]` with ISO-8601 `timestamp`.

### `GET /analytics/alerts?camera_id=cam-01&limit=100`

Recent crowd alerts (threshold breaches).

```json
[
  {
    "id": 12,
    "camera_id": "cam-01",
    "timestamp": "2026-07-22T10:15:03Z",
    "level": "critical",
    "kind": "crowd",
    "message": "Crowd threshold exceeded: 62 people (≥50); density 0.91 (≥0.75)",
    "people_count": 62,
    "max_density": 0.91,
    "acknowledged": false
  }
]
```

---

## Heatmap & Streaming

### `GET /heatmap/latest?camera_id=cam-01`

```json
{
  "camera_id": "cam-01",
  "timestamp": 1721650000.42,
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "people_count": 37,
  "max_density": 0.74
}
```

### `GET /stream/mjpeg?camera_id=cam-01&kind=overlay`

`multipart/x-mixed-replace` MJPEG stream. `kind` = `overlay` (heatmap) or `raw`
(original preview). Embed directly in an `<img src>`.

### `WS /stream/live?camera_id=cam-01&include_image=1&fps=15`

WebSocket. The server pushes a message per new frame:

```json
{
  "type": "frame",
  "status": { "camera_id": "cam-01", "running": true, "connected": true, "fps": 24.6, "people_count": 37, "last_frame_at": 1721650000.42 },
  "analytics": { "...": "see /analytics/current" },
  "image": "data:image/jpeg;base64,..."   // omitted when include_image=0
}
```

Query params: `camera_id` (required), `include_image` (`1`/`0`, default `1`),
`fps` (client cap, ≤ server `TARGET_FPS`).

---

## Error format

FastAPI standard:

```json
{ "detail": "Camera not found" }
```

Common codes: `404` unknown camera / no analytics, `409` camera limit reached,
`425` frame not processed yet, `422` validation error.

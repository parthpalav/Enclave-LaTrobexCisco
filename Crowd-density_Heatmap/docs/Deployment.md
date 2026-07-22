# Deployment

## 1. Configuration

Everything is configured via environment variables. Copy the template and edit:

```bash
cp backend/.env.example backend/.env
```

Key values: `DATABASE_URL`, `REDIS_URL`, `YOLO_DEVICE`, `YOLO_MODEL`,
`HEATMAP_SIGMA`, `HEATMAP_ALPHA`, `TARGET_FPS`, `MAX_CAMERAS`,
`ALERT_*`. Full list in `backend/.env.example`.

## 2. Docker Compose (recommended)

From the repo root:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Services & ports:

| Service   | Port | URL |
|-----------|------|-----|
| frontend  | 8080 | http://localhost:8080 |
| backend   | 8000 | http://localhost:8000/docs |
| postgres  | 5432 | — |
| redis     | 6379 | — |

Compose sets `DATABASE_URL`/`REDIS_URL` to the internal service hostnames
automatically. Override Postgres creds with `POSTGRES_USER/PASSWORD/DB` env vars.

Model weights download once and persist in the `models` named volume.

## 3. GPU / CUDA

CPU works out of the box. For GPU:

1. Install the **NVIDIA Container Toolkit** on the host.
2. In `docker/Dockerfile.backend`, base off a CUDA runtime image and install a
   CUDA torch wheel, e.g.:
   ```dockerfile
   RUN pip install torch==2.5.1 torchvision==0.20.1 \
       --index-url https://download.pytorch.org/whl/cu121
   ```
3. Uncomment the `deploy.resources.reservations.devices` block for the `backend`
   service in `docker/docker-compose.yml`.
4. Set `YOLO_DEVICE=cuda` (or `auto`) and optionally `YOLO_HALF_PRECISION=true`.

Verify: `GET /api/v1/health` should report `"device": "cuda:0"`.

## 4. Bare-metal / VM

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# For GPU, reinstall torch from the CUDA index (see above).
export $(grep -v '^#' .env | xargs)   # or use a process manager
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> Run a **single worker per process** — camera pipelines hold in-process state.
> Scale by running more *instances* (each owning distinct cameras), not workers.

Frontend:

```bash
cd frontend
npm install && npm run build      # static files in dist/
# serve dist/ with nginx (see frontend/nginx.conf) or any static host
```

## 5. Database migrations

`init_db()` auto-creates tables on startup for convenience. For production,
manage schema with **Alembic** (already in requirements): generate a migration
from `app.database.models` and run it in your release pipeline instead of relying
on auto-create.

## 6. Health checks & logging

- Health: `GET /api/v1/health` (also wired as the Docker `HEALTHCHECK`).
- Logs: plain text by default; set `LOG_JSON=true` for structured logs suitable
  for aggregation (ELK/Loki/CloudWatch).

## 7. Cloud notes

- **Any container host** works (ECS/Fargate, GKE, Azure Container Apps, Fly.io,
  Render). Expose 8000 (backend) and 8080/80 (frontend).
- Use a **managed Postgres** (RDS/Cloud SQL/Neon) and **managed Redis**; point
  `DATABASE_URL`/`REDIS_URL` at them.
- For RTSP ingest, ensure the host can reach the camera network (VPN/VPC peering).
- Terminate TLS at a load balancer; WebSockets upgrade over `wss://` — the nginx
  config already forwards `Upgrade`/`Connection` headers.

## 8. CI/CD

`.github/workflows/ci.yml` runs on push/PR:

1. **backend** — ruff lint + pytest (pipeline tests, offline-safe).
2. **frontend** — typecheck + Vite build.
3. **docker** — builds both images.

Extend the `docker` job with a registry push + deploy step for your target.

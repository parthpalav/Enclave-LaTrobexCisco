"""Persistence + caching service.

Writes analytics/alerts to PostgreSQL and mirrors the latest analytics into
Redis for fast cross-process reads. Raw CCTV frames are never persisted unless
``store_raw_video`` is explicitly enabled.

The database is **optional**: if it is unavailable (e.g. running the engine on a
laptop with no PostgreSQL), persistence self-disables after one warning and the
live pipeline — detection, tracking, heatmap, in-memory analytics — keeps
working. Nothing here ever raises up into an API request.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.database import models
from app.database.session import SessionLocal
from app.services.camera_service import CameraManager

logger = get_logger(__name__)


class StorageService:
    """Async persistence for analytics, alerts and the latest-analytics cache."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._redis = None
        # Database availability — flips to False on the first connection error so
        # we stop hammering a DB that isn't there (and stop flooding the logs).
        self._db_ok = True
        self._db_warned = False

    # ------------------------------------------------------------------ #
    # Availability helpers
    # ------------------------------------------------------------------ #
    def _note_db_error(self, exc: Exception) -> None:
        self._db_ok = False
        if not self._db_warned:
            logger.warning(
                "Database unavailable (%s). Analytics persistence is DISABLED for "
                "this session; the live heatmap keeps working. Start PostgreSQL "
                "(or use the SQLite default) and restart to enable storage.",
                exc,
            )
            self._db_warned = True

    @property
    def db_enabled(self) -> bool:
        return self._db_ok

    async def connect_redis(self) -> None:
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self.settings.redis_url, decode_responses=True
            )
            await self._redis.ping()
            logger.info("Connected to Redis at %s", self.settings.redis_url)
        except Exception as exc:  # noqa: BLE001 - Redis is optional
            logger.warning("Redis unavailable (%s); continuing without cache", exc)
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()

    # ------------------------------------------------------------------ #
    # Camera metadata
    # ------------------------------------------------------------------ #
    async def upsert_camera(self, data: dict) -> None:
        if not self._db_ok:
            return
        try:
            async with SessionLocal() as session:
                existing = await session.scalar(
                    select(models.Camera).where(
                        models.Camera.camera_id == data["camera_id"]
                    )
                )
                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    session.add(models.Camera(**data))
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)

    async def delete_camera(self, camera_id: str) -> None:
        if not self._db_ok:
            return
        try:
            async with SessionLocal() as session:
                cam = await session.scalar(
                    select(models.Camera).where(models.Camera.camera_id == camera_id)
                )
                if cam:
                    await session.delete(cam)
                    await session.commit()
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)

    async def list_cameras(self) -> list[models.Camera]:
        if not self._db_ok:
            return []
        try:
            async with SessionLocal() as session:
                rows = await session.scalars(select(models.Camera))
                return list(rows)
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)
            return []

    # ------------------------------------------------------------------ #
    # Analytics
    # ------------------------------------------------------------------ #
    async def save_analytics(self, payload: dict) -> None:
        # Always refresh the (optional) Redis cache, even without a database.
        await self._cache_latest(payload)

        if not self._db_ok:
            return
        try:
            record = models.FrameAnalytics(
                camera_id=payload["camera_id"],
                timestamp=datetime.fromtimestamp(payload["timestamp"], tz=timezone.utc),
                people_count=payload["people_count"],
                density_score=payload["density_score"],
                average_density=payload["average_density"],
                max_density=payload["max_density"],
                crowd_level=payload.get("crowd_level", "low"),
                crowded_zones=payload.get("crowded_zones", []),
                movement_index=payload.get("movement_index", 0.0),
                fps=payload.get("fps", 0.0),
            )
            async with SessionLocal() as session:
                session.add(record)
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)

    async def _cache_latest(self, payload: dict) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(
                f"analytics:latest:{payload['camera_id']}",
                json.dumps(payload),
                ex=self.settings.redis_ttl_seconds,
            )
        except Exception:  # noqa: BLE001
            pass

    async def get_cached_latest(self, camera_id: str) -> dict | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(f"analytics:latest:{camera_id}")
            return json.loads(raw) if raw else None
        except Exception:  # noqa: BLE001
            return None

    async def analytics_history(
        self, camera_id: str, minutes: int = 60, limit: int = 500
    ) -> list[models.FrameAnalytics]:
        if not self._db_ok:
            return []
        try:
            since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            async with SessionLocal() as session:
                rows = await session.scalars(
                    select(models.FrameAnalytics)
                    .where(
                        models.FrameAnalytics.camera_id == camera_id,
                        models.FrameAnalytics.timestamp >= since,
                    )
                    .order_by(models.FrameAnalytics.timestamp.desc())
                    .limit(limit)
                )
                return list(rows)
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)
            return []

    # ------------------------------------------------------------------ #
    # Alerts
    # ------------------------------------------------------------------ #
    async def maybe_raise_alert(self, payload: dict) -> models.Alert | None:
        if not self._db_ok:
            return None
        people = payload.get("people_count", 0)
        max_density = payload.get("max_density", 0.0)
        reasons = []
        if people >= self.settings.alert_people_threshold:
            reasons.append(f"{people} people (≥{self.settings.alert_people_threshold})")
        if max_density >= self.settings.alert_density_threshold:
            reasons.append(
                f"density {max_density:.2f} (≥{self.settings.alert_density_threshold})"
            )
        if not reasons:
            return None

        level = "critical" if max_density >= 0.9 or people >= (
            self.settings.alert_people_threshold * 1.5
        ) else "warning"

        try:
            alert = models.Alert(
                camera_id=payload["camera_id"],
                level=level,
                kind="crowd",
                message="Crowd threshold exceeded: " + "; ".join(reasons),
                people_count=people,
                max_density=max_density,
            )
            async with SessionLocal() as session:
                session.add(alert)
                await session.commit()
                await session.refresh(alert)
            logger.info(
                "Alert (%s) on camera '%s': %s", level, payload["camera_id"], alert.message
            )
            return alert
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)
            return None

    async def list_alerts(self, camera_id: str | None = None, limit: int = 100):
        if not self._db_ok:
            return []
        try:
            async with SessionLocal() as session:
                stmt = (
                    select(models.Alert)
                    .order_by(models.Alert.timestamp.desc())
                    .limit(limit)
                )
                if camera_id:
                    stmt = stmt.where(models.Alert.camera_id == camera_id)
                rows = await session.scalars(stmt)
                return list(rows)
        except Exception as exc:  # noqa: BLE001
            self._note_db_error(exc)
            return []


# --------------------------------------------------------------------------- #
# Background persistence loop
# --------------------------------------------------------------------------- #
async def persistence_loop(
    manager: CameraManager, storage: StorageService, stop_event: asyncio.Event
) -> None:
    """Periodically persist the latest analytics from every active camera.

    Decouples the blocking pipeline threads from async DB writes: we sample the
    published latest analytics at a fixed cadence rather than writing on every
    frame. If the database is unavailable this loop still refreshes the Redis
    cache (if any) and otherwise idles cheaply.
    """
    settings = storage.settings
    period = max(0.5, settings.analytics_persist_interval / max(1, settings.target_fps))
    logger.info("Persistence loop started (every %.2fs)", period)

    while not stop_event.is_set():
        try:
            for pipeline in list(manager._pipelines.values()):  # noqa: SLF001
                payload = pipeline.latest_analytics()
                if not payload:
                    continue
                status = pipeline.snapshot_status()
                payload = {**payload, "fps": status.get("fps", 0.0)}
                await storage.save_analytics(payload)
                await storage.maybe_raise_alert(payload)
        except Exception:  # noqa: BLE001
            logger.exception("Persistence loop iteration failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=period)
        except asyncio.TimeoutError:
            pass

    logger.info("Persistence loop stopped")


_storage: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage

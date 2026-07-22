"""SQLAlchemy ORM models.

Only analytics and metadata are persisted. Raw CCTV frames are NEVER written
to the database (see ``Settings.store_raw_video``, disabled by default).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(Text, doc="RTSP/HTTP URL, device index or file")
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    analytics: Mapped[list["FrameAnalytics"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )


class FrameAnalytics(Base):
    __tablename__ = "frame_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("cameras.camera_id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    people_count: Mapped[int] = mapped_column(Integer, default=0)
    density_score: Mapped[float] = mapped_column(Float, default=0.0)
    average_density: Mapped[float] = mapped_column(Float, default=0.0)
    max_density: Mapped[float] = mapped_column(Float, default=0.0)
    crowd_level: Mapped[str] = mapped_column(String(16), default="low")
    crowded_zones: Mapped[dict] = mapped_column(JSON, default=list)
    movement_index: Mapped[float] = mapped_column(Float, default=0.0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)

    camera: Mapped["Camera"] = relationship(back_populates="analytics")


class HeatmapHistory(Base):
    __tablename__ = "heatmap_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("cameras.camera_id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    # A compact heatmap snapshot (downscaled JPEG, base64) — analytics artefact,
    # not raw video. Stored only when snapshotting is enabled.
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    people_count: Mapped[int] = mapped_column(Integer, default=0)
    max_density: Mapped[float] = mapped_column(Float, default=0.0)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("cameras.camera_id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    level: Mapped[str] = mapped_column(String(16), default="warning")
    kind: Mapped[str] = mapped_column(String(32), default="crowd")
    message: Mapped[str] = mapped_column(Text)
    people_count: Mapped[int] = mapped_column(Integer, default=0)
    max_density: Mapped[float] = mapped_column(Float, default=0.0)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    camera: Mapped["Camera"] = relationship(back_populates="alerts")

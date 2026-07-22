"""Dynamic location management endpoint."""

from __future__ import annotations

import logging
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/location", tags=["location"])


class LocationUpdate(BaseModel):
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    location: str | None = Field(default=None, description="Optional location description or city name")


# In-memory dynamic location state
_current_location = {
    "latitude": 0.0,
    "longitude": 0.0,
    "location": "Waiting for Dynamic Location",
    "source": "uninitialized",
}


@router.post("/update", status_code=status.HTTP_200_OK)
async def update_location(payload: LocationUpdate) -> dict:
    """Update real-time dynamic location coordinates from browser HTML5 Geolocation or Antigravity client."""
    global _current_location
    loc_name = payload.location
    if not loc_name:
        loc_name = f"GPS ({payload.latitude:.4f}, {payload.longitude:.4f})"

    _current_location = {
        "latitude": round(payload.latitude, 6),
        "longitude": round(payload.longitude, 6),
        "location": loc_name,
        "source": "dynamic_gps",
    }
    logger.info("Dynamic location updated: %s (%f, %f)", loc_name, payload.latitude, payload.longitude)
    return {"status": "ok", "current": _current_location}


@router.get("/current")
async def get_current_location() -> dict:
    """Return the current dynamic location coordinates."""
    return _current_location

"""API smoke tests using httpx ASGI transport (no server, no GPU)."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    prefix = get_settings().api_prefix
    async with client:
        resp = await client.get(f"{prefix}/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "device" in body
    assert body["cameras_active"] >= 0


@pytest.mark.asyncio
async def test_root(client):
    async with client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "service" in resp.json()


@pytest.mark.asyncio
async def test_camera_list_empty(client):
    prefix = get_settings().api_prefix
    async with client:
        resp = await client.get(f"{prefix}/camera/list")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_current_analytics_404_when_unknown(client):
    prefix = get_settings().api_prefix
    async with client:
        resp = await client.get(f"{prefix}/analytics/current", params={"camera_id": "nope"})
    assert resp.status_code == 404

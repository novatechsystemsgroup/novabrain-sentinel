"""Vertical-slice smoke tests: health endpoint and landing page."""

import asyncio

import httpx

from sentinel.api import app


def get(path: str):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(request())


def test_health_returns_ok():
    response = get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "novabrain-sentinel"}


CONSOLE_MARKERS = (
    "NovaBrain Sentinel",
    "ONLINE",
    "OBSERVE",
    "LEARN",
    "Run Demo Incident",
    "Real NVIDIA inference",
    "Safe simulated remediation",
)


def test_landing_page_renders():
    response = get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    for marker in CONSOLE_MARKERS:
        assert marker in body, f"console is missing {marker!r}"

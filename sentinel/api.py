"""HTTP surface for the NovaBrain Sentinel vertical slice."""

import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from .analysis import analyze_event
from .nvidia import ProviderError
from .schemas import IncidentAnalysis, IncidentEvent

SERVICE_NAME = "novabrain-sentinel"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

PROVIDER_ERROR_STATUS = {
    "provider_not_configured": 503,
    "provider_timeout": 504,
    "provider_unavailable": 502,
    "invalid_model_response": 502,
}

logger = logging.getLogger("sentinel.analysis")


def create_app(llm_transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    app = FastAPI(title="NovaBrain Sentinel")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.get("/")
    def landing() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/v1/incidents/analyze", response_model=IncidentAnalysis)
    async def analyze_incident(event: IncidentEvent) -> IncidentAnalysis:
        return await analyze_event(event, transport=llm_transport)

    @app.exception_handler(ProviderError)
    async def on_provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        logger.warning("incident analysis failed: %s", exc.code)
        return JSONResponse(
            status_code=PROVIDER_ERROR_STATUS.get(exc.code, 502),
            content={"detail": {"error": exc.code, "message": exc.message}},
        )

    return app


app = create_app()

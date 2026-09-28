"""HTTP surface for the NovaBrain Sentinel vertical slice."""

import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .analysis import analyze_event
from .nvidia import ProviderError
from .schemas import (
    DecisionRequest,
    ExecuteRequest,
    IncidentAnalysis,
    IncidentEvent,
    IncidentWorkflow,
)
from .workflow import WORKFLOW_ERROR_STATUS, WorkflowError, WorkflowStore

SERVICE_NAME = "novabrain-sentinel"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Scoped to the console document alone, never to middleware: /docs, /health and
# the API responses must keep working while the page is locked to its own assets.
CONSOLE_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'"
)

PROVIDER_ERROR_STATUS = {
    "provider_not_configured": 503,
    "provider_timeout": 504,
    "provider_unavailable": 502,
    "invalid_model_response": 502,
}

logger = logging.getLogger("sentinel.analysis")


def create_app(
    llm_transport: httpx.AsyncBaseTransport | None = None,
    store: WorkflowStore | None = None,
) -> FastAPI:
    app = FastAPI(title="NovaBrain Sentinel")
    workflow_store = store or WorkflowStore()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.get("/")
    def landing() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html", headers={"Content-Security-Policy": CONSOLE_CSP}
        )

    @app.post("/api/v1/incidents/analyze", response_model=IncidentAnalysis)
    async def analyze_incident(event: IncidentEvent) -> IncidentAnalysis:
        analysis = await analyze_event(event, transport=llm_transport)
        workflow_store.record_analysis(event, analysis)
        return analysis

    @app.get("/api/v1/incidents/{incident_id}", response_model=IncidentWorkflow)
    def get_incident(incident_id: str) -> IncidentWorkflow:
        return workflow_store.get(incident_id)

    @app.post("/api/v1/incidents/{incident_id}/approve", response_model=IncidentWorkflow)
    def approve_incident(
        incident_id: str, body: DecisionRequest | None = None
    ) -> IncidentWorkflow:
        return workflow_store.decide(incident_id, "approved", body.note if body else None)

    @app.post("/api/v1/incidents/{incident_id}/reject", response_model=IncidentWorkflow)
    def reject_incident(incident_id: str, body: DecisionRequest | None = None) -> IncidentWorkflow:
        return workflow_store.decide(incident_id, "rejected", body.note if body else None)

    @app.post("/api/v1/incidents/{incident_id}/execute", response_model=IncidentWorkflow)
    def execute_incident(incident_id: str, body: ExecuteRequest) -> IncidentWorkflow:
        return workflow_store.execute(incident_id, body.action, body.note)

    @app.exception_handler(ProviderError)
    async def on_provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        logger.warning("incident analysis failed: %s", exc.code)
        return JSONResponse(
            status_code=PROVIDER_ERROR_STATUS.get(exc.code, 502),
            content={"detail": {"error": exc.code, "message": exc.message}},
        )

    @app.exception_handler(WorkflowError)
    async def on_workflow_error(request: Request, exc: WorkflowError) -> JSONResponse:
        logger.info("workflow refused a transition: %s", exc.code)
        return JSONResponse(
            status_code=WORKFLOW_ERROR_STATUS.get(exc.code, 409),
            content={"detail": {"error": exc.code, "message": exc.message}},
        )

    return app


app = create_app()

"""HTTP surface for the NovaBrain Sentinel vertical slice."""

import logging
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .analysis import analyze_event
from .ingestion import (
    INGEST_ERROR_STATUS,
    EventInProgress,
    IdempotencyLedger,
    IngestError,
    require_ingest_token,
)
from .nvidia import ProviderError
from .schemas import (
    DecisionRequest,
    ExecuteRequest,
    IncidentAnalysis,
    IncidentEvent,
    IncidentWorkflow,
    IngestEvidence,
    IngestResponse,
    OperationalEvent,
)
from .workflow import WORKFLOW_ERROR_STATUS, WorkflowError, WorkflowStore, utc_now

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
    ingest_ledger: IdempotencyLedger | None = None,
) -> FastAPI:
    app = FastAPI(title="NovaBrain Sentinel")
    workflow_store = store or WorkflowStore()
    ledger = ingest_ledger or IdempotencyLedger()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def ingest_body(event_id: str, record: IncidentWorkflow, duplicate: bool) -> dict:
        """The same pointer for a first receipt and a replay: one incident, one path."""
        path = f"/?incident={record.incident_id}"
        return IngestResponse(
            event_id=event_id,
            incident_id=record.incident_id,
            workflow_state=record.state,
            duplicate=duplicate,
            console_path=path,
        ).model_dump()

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

    @app.post("/api/v1/events/ingest")
    async def ingest_event(
        event: OperationalEvent, _: None = Depends(require_ingest_token)
    ) -> JSONResponse:
        """Machine-to-machine entry point: normalise, deduplicate, then hand over.

        The analysis and the approval policy behind this route are the ones the
        console already uses; ingestion adds no second workflow. It runs the
        inference synchronously, so a producer's own timeout has to clear the
        model's, not the other way round.
        """
        incident = event.to_incident_event()
        received_at = utc_now()
        incident_id = ledger.reserve(event.event_id)
        if incident_id is not None and not workflow_store.holds(incident_id):
            # A finished entry whose incident has been evicted is a gap in memory,
            # not a replay: forget the stale pointer and treat the event as new.
            if not ledger.discard(event.event_id):
                raise EventInProgress(event.event_id)
            incident_id = ledger.reserve(event.event_id)
        if incident_id is not None:
            replay = workflow_store.get(incident_id)
            return JSONResponse(
                status_code=200,
                content=ingest_body(event.event_id, replay, True),
            )

        try:
            analysis = await analyze_event(incident, transport=llm_transport)
            record = workflow_store.record_analysis(
                incident,
                analysis,
                ingest=IngestEvidence(
                    event_id=event.event_id,
                    source=event.source,
                    event_type=event.event_type,
                    observed_at=event.observed_at_or(received_at),
                    received_at=received_at,
                ),
            )
        except Exception:
            # Nothing was concluded, so nothing is remembered: the producer may retry.
            ledger.release(event.event_id)
            raise
        ledger.complete(event.event_id, record.incident_id)
        body = ingest_body(event.event_id, record, False)
        return JSONResponse(
            status_code=201, content=body, headers={"Location": body["console_path"]}
        )

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

    @app.exception_handler(IngestError)
    async def on_ingest_error(request: Request, exc: IngestError) -> JSONResponse:
        logger.warning("ingestion refused: %s", exc.code)
        return JSONResponse(
            status_code=INGEST_ERROR_STATUS.get(exc.code, 400),
            content={"detail": {"error": exc.code, "message": exc.message}},
            headers={"WWW-Authenticate": "Bearer"} if exc.code == "invalid_ingest_token" else None,
        )

    return app


app = create_app()

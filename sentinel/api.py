"""HTTP surface for the NovaBrain Sentinel vertical slice."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

SERVICE_NAME = "novabrain-sentinel"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="NovaBrain Sentinel")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.get("/")
    def landing() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()

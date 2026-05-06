"""spec1_api — FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from spec1_api import __version__
from spec1_api.routers import (
    brief,
    calibration,
    cycle,
    fara,
    health,
    intel,
    leads,
    psyop,
    signals,
    verdicts,
)
from spec1_api.routers import nodes, ingest
from spec1_api.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

# Origins allowed to call the API (viz dev servers + file:// via "null")
_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "null",  # file:// origin sent by browsers
]
_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start/stop scheduler."""
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SPEC-1 Intelligence API",
        description="Real-time OSINT intelligence engine API",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @app.get("/", include_in_schema=False)
    async def ui_root() -> FileResponse:
        """Serve the SPEC-1 UI."""
        path = _STATIC_DIR / "index.html"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="UI not found")
        return FileResponse(path, media_type="text/html")

    app.include_router(health.router)
    app.include_router(signals.router)
    app.include_router(intel.router)
    app.include_router(leads.router)
    app.include_router(brief.router)
    app.include_router(psyop.router)
    app.include_router(fara.router)
    app.include_router(cycle.router)
    app.include_router(verdicts.router)
    app.include_router(calibration.router)
    app.include_router(nodes.router)
    app.include_router(ingest.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("SPEC1_API_HOST", "127.0.0.1")
    port = int(os.environ.get("SPEC1_API_PORT", "8000"))
    uvicorn.run("spec1_api.main:app", host=host, port=port, reload=False)

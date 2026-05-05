"""Publication router — GET /publication/latest."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/publication", tags=["publication"])

_BRIEFS_DIR = Path("generated/briefs")


@router.get("/latest")
def get_latest_publication() -> FileResponse:
    """Return the most recently generated publication PDF."""
    pdfs = list(_BRIEFS_DIR.glob("spec1_issue_*.pdf")) if _BRIEFS_DIR.exists() else []
    if not pdfs:
        raise HTTPException(status_code=404, detail="No publication PDFs found")
    latest = max(pdfs, key=lambda p: p.stat().st_mtime)
    return FileResponse(
        path=str(latest),
        media_type="application/pdf",
        filename=latest.name,
    )


@router.get("/list")
def list_publications() -> dict:
    """Return metadata for all generated publication PDFs, newest first."""
    pdfs = sorted(_BRIEFS_DIR.glob("spec1_issue_*.pdf")) if _BRIEFS_DIR.exists() else []
    items = [
        {"filename": p.name, "size_bytes": p.stat().st_size}
        for p in reversed(pdfs)
    ]
    return {"total": len(items), "items": items}

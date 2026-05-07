"""Publication router — GET /publication/latest."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/publication", tags=["publication"])

_BRIEFS_DIR = Path("generated/briefs")


def _latest_pdf() -> Path | None:
    """Return the most recently modified spec1_issue_*.pdf in generated/briefs/."""
    if not _BRIEFS_DIR.exists():
        return None
    pdfs = sorted(_BRIEFS_DIR.glob("spec1_issue_*.pdf"), key=lambda p: p.stat().st_mtime)
    return pdfs[-1] if pdfs else None


@router.get("/latest")
def get_latest_publication() -> FileResponse:
    """Return the most recent publication PDF as a file download."""
    pdf = _latest_pdf()
    if pdf is None:
        raise HTTPException(status_code=404, detail="No publication PDF found")
    return FileResponse(
        path=str(pdf),
        media_type="application/pdf",
        filename=pdf.name,
    )


@router.get("")
def list_publications() -> dict:
    """List all available publication PDFs, newest first."""
    if not _BRIEFS_DIR.exists():
        return {"total": 0, "items": []}
    pdfs = sorted(_BRIEFS_DIR.glob("spec1_issue_*.pdf"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "total": len(pdfs),
        "items": [p.name for p in pdfs],
    }

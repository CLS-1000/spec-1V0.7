"""Publication router — GET /publication/latest."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/publication", tags=["publication"])

_BRIEFS_DIR = Path("briefs")


def _latest_pdf() -> Path | None:
    """Return the most recently created spec1_issue_*.pdf in briefs/."""
    if not _BRIEFS_DIR.exists():
        return None
    pdfs = sorted(_BRIEFS_DIR.glob("spec1_issue_*.pdf"))
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
    pdfs = sorted(_BRIEFS_DIR.glob("spec1_issue_*.pdf"), reverse=True)
    return {
        "total": len(pdfs),
        "items": [p.name for p in pdfs],
    }

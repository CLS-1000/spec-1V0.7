"""Publication router — GET /publication/latest, GET /publication/list."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/publication", tags=["publication"])

_BRIEFS_DIR = Path("generated/briefs")


def _safe_pdf_path(p: Path) -> Path:
    """Resolve path and ensure it stays within _BRIEFS_DIR (no symlink escape)."""
    resolved = p.resolve()
    base = _BRIEFS_DIR.resolve()
    if p.is_symlink() or not str(resolved).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access denied")
    return resolved


@router.get("/latest")
def get_latest_publication() -> FileResponse:
    """Return the most recently generated publication PDF."""
    pdfs = list(_BRIEFS_DIR.glob("spec1_issue_*.pdf")) if _BRIEFS_DIR.exists() else []
    if not pdfs:
        raise HTTPException(status_code=404, detail="No publication PDFs found")
    latest = max(pdfs, key=lambda p: p.stat().st_mtime)
    safe = _safe_pdf_path(latest)
    return FileResponse(
        path=str(safe),
        media_type="application/pdf",
        filename=latest.name,
    )


@router.get("/list")
def list_publications() -> dict:
    """Return metadata for all generated publication PDFs, newest first."""
    pdfs = list(_BRIEFS_DIR.glob("spec1_issue_*.pdf")) if _BRIEFS_DIR.exists() else []
    pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    items = [
        {"filename": p.name, "size_bytes": p.stat().st_size}
        for p in pdfs
        if not p.is_symlink()
    ]
    return {"total": len(items), "items": items}

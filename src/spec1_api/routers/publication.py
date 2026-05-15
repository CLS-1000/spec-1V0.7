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
    if p.is_symlink() or not resolved.is_relative_to(base):
        raise HTTPException(status_code=403, detail="Access denied")
    return resolved


def _real_pdfs() -> list[Path]:
    """Return non-symlink spec1_issue_*.pdf paths under _BRIEFS_DIR."""
    if not _BRIEFS_DIR.exists():
        return []
    return [p for p in _BRIEFS_DIR.glob("spec1_issue_*.pdf") if not p.is_symlink()]


def _pdf_sort_key(p: Path) -> tuple:
    """Sort key: (mtime, filename) — mtime for recency, filename for stable tie-break."""
    return (p.stat().st_mtime, p.name)


@router.get("/latest")
def get_latest_publication() -> FileResponse:
    """Return the most recently generated publication PDF."""
    pdfs = _real_pdfs()
    if not pdfs:
        raise HTTPException(status_code=404, detail="No publication PDFs found")
    latest = max(pdfs, key=_pdf_sort_key)
    safe = _safe_pdf_path(latest)
    return FileResponse(
        path=str(safe),
        media_type="application/pdf",
        filename=latest.name,
    )


@router.get("/list")
def list_publications() -> dict:
    """Return metadata for all generated publication PDFs, newest first."""
    pdfs = sorted(_real_pdfs(), key=_pdf_sort_key, reverse=True)
    items = [{"filename": p.name, "size_bytes": p.stat().st_size} for p in pdfs]
    return {"total": len(items), "items": items}

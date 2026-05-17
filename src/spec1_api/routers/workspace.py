"""Workspace router — GET/POST /workspace/cases."""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["workspace"])


class OpenCaseRequest(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=500, strip_whitespace=True)]
    question: Annotated[str, Field(min_length=1, max_length=500, strip_whitespace=True)]
    tags: Annotated[list[Annotated[str, Field(max_length=100, strip_whitespace=True)]], Field(max_length=20)] = []


@router.get("/cases")
def list_cases(
    status: Optional[str] = Query(None, description="Filter by status: OPEN, CLOSED, WATCHING"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """List investigation cases, optionally filtered by status."""
    try:
        from spec1_engine.workspace.case import list_cases as _list
        cases = _list(status=status.upper() if status else None)
    except Exception:
        logger.exception("Failed to load workspace cases")
        raise HTTPException(status_code=500, detail="Could not load cases") from None
    total = len(cases)
    page = cases[offset: offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "items": [c.to_dict() for c in page]}


@router.post("/cases")
def open_case(req: OpenCaseRequest) -> dict:
    """Open a new investigation case."""
    try:
        from spec1_engine.workspace.case import open_case as _open
        case = _open(title=req.title, question=req.question, tags=req.tags)
        return case.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    """Get a specific case by ID."""
    try:
        from spec1_engine.workspace.case import get_case as _get
        return _get(case_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found") from exc


@router.post("/cases/{case_id}/close")
def close_case(case_id: str) -> dict:
    """Close an investigation case and generate its final report."""
    try:
        from spec1_engine.workspace.case import close_case as _close
        return _close(case_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

"""Adapters router — GET /adapters, GET /adapters/{name}."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from cls_osint.adapters.registry import get_adapter, list_adapters

router = APIRouter(prefix="/adapters", tags=["adapters"])


@router.get("")
def list_all_adapters(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    active_only: bool = Query(False, description="Only return active adapters"),
) -> dict:
    """Return all registered signal adapters (marketplace catalogue)."""
    adapters = list_adapters(source_type=source_type, active_only=active_only)
    return {
        "total": len(adapters),
        "adapters": [
            {
                "name": a.name,
                "source_type": a.source_type,
                "description": a.description,
                "version": a.version,
                "author": a.author,
                "tags": a.tags,
                "active": a.active,
            }
            for a in adapters
        ],
    }


@router.get("/{name}")
def get_adapter_detail(name: str) -> dict:
    """Return details for a specific adapter by name."""
    info = get_adapter(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Adapter '{name}' not found")
    return {
        "name": info.name,
        "source_type": info.source_type,
        "description": info.description,
        "version": info.version,
        "author": info.author,
        "tags": info.tags,
        "active": info.active,
    }

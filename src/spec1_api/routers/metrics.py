# @domain:   machine
# @module:   routers_metrics
# @loc:      gh_main
# @status:   stable
# @depends:  spec1_core, cls_db

"""Metrics router — GET /metrics and GET /metrics/json."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from spec1_api import metrics as _m

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_class=PlainTextResponse)
def prometheus_metrics() -> str:
    """Return metrics in Prometheus exposition format (text/plain; version=0.0.4)."""
    return _m.get_prometheus_text()


@router.get("/json")
def json_metrics() -> dict:
    """Return all collected metrics as JSON."""
    return _m.get_metrics_dict()

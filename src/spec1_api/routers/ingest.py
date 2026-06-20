# @domain:   machine
# @module:   routers_ingest
# @loc:      gh_main
# @status:   stable
# @depends:  spec1_core, cls_db

"""Ingest router — POST /api/v1/ingest/signal

Single-writer endpoint for the n8n crawler → SPEC-1 signal loop.
Accepts a CrawlerPayload, runs the 4-gate pipeline, and appends the
result to political_signals.  Gate FAIL rows are still written.

Invariants:
  - No UPDATE or DELETE — append-only
  - Duplicate signal_id: silent skip, written=False
  - All datetimes UTC
  - run_id on every written row
  - Gate threshold imported from spec1_core.signal.gates (never hardcoded)
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from spec1_api.db.signals import get_prior_summaries, insert_signal
from spec1_api.routers.nodes import NODE_REGISTRY
from spec1_api.schemas.node_signal import (
    CrawlerPayload,
    GateScores,
    GateStatus,
    IngestResult,
)
from spec1_core.signal.gates import (
    score_credibility,
    score_novelty,
    score_velocity,
    score_volume,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_signal_id(node_id: str, source_url: str, published_at: str) -> str:
    """Deterministic UUID derived from sha256(node_id + source_url + published_at)."""
    raw = f"{node_id}{source_url}{published_at}".encode()
    digest = hashlib.sha256(raw).digest()
    return str(uuid.UUID(bytes=digest[:16]))


def _make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _extract_summary(body: str, max_chars: int = 400) -> str:
    """First 3 sentences of *body*, truncated to *max_chars*."""
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    summary = " ".join(sentences[:3])
    return summary[:max_chars]


def _age_hours(published_at: datetime) -> float:
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600)


def _freshness(age_h: float) -> str:
    if age_h < 6:
        return "LIVE"
    if age_h < 24:
        return "RECENT"
    return "STALE"


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/signal", response_model=IngestResult)
async def ingest_signal(payload: CrawlerPayload) -> IngestResult:
    """Accept a crawler signal, run 4-gate scoring, and persist it."""
    if payload.node_id not in NODE_REGISTRY:
        raise HTTPException(status_code=422, detail=f"Unknown node_id: {payload.node_id!r}")

    # Enforce UTC — reject naive datetimes, normalise any non-UTC offset
    pub = payload.published_at
    if pub.tzinfo is None:
        raise HTTPException(status_code=422, detail="published_at must be timezone-aware (UTC required)")
    pub_utc = pub.astimezone(timezone.utc)
    pub_iso = pub_utc.isoformat()
    signal_id = _make_signal_id(payload.node_id, payload.source_url, pub_iso)
    run_id = _make_run_id()
    retrieved_at = datetime.now(timezone.utc)

    # Fetch prior PASS summaries for novelty scoring
    prior_summaries = await get_prior_summaries(payload.node_id, n=20)

    # Score all 4 gates
    cred = score_credibility(payload.source_domain)
    vol = score_volume(payload.tags)
    vel = score_velocity(pub_utc)
    nov = score_novelty(payload.body, prior_summaries)
    age_h = _age_hours(pub_utc)

    gates = GateScores(
        credibility=round(cred, 4),
        volume=round(vol, 4),
        velocity=round(vel, 4),
        novelty=round(nov, 4),
    )
    gate_status = GateStatus.PASS if gates.all_pass() else GateStatus.FAIL

    summary = _extract_summary(payload.body)

    logger.info(
        "ingest node=%s signal=%s status=%s cred=%.4f vol=%.4f vel=%.4f nov=%.4f",
        payload.node_id,
        signal_id,
        gate_status.value,
        gates.credibility,
        gates.volume,
        gates.velocity,
        gates.novelty,
    )

    row = {
        "signal_id":       signal_id,
        "node_id":         payload.node_id,
        "run_id":          run_id,
        "headline":        payload.headline,
        "summary":         summary,
        "source_url":      payload.source_url,
        "source_domain":   payload.source_domain,
        "published_at":    pub_iso,
        "retrieved_at":    retrieved_at.isoformat(),
        "gate_status":     gate_status.value,
        "gate_credibility":gates.credibility,
        "gate_volume":     gates.volume,
        "gate_velocity":   gates.velocity,
        "gate_novelty":    gates.novelty,
        "signal_age_hours":round(age_h, 4),
        "freshness_label": _freshness(age_h),
        "analyst_voice":   payload.analyst_voice,
        "conflict_score":  payload.conflict_score,
        "tags":            payload.tags,
    }

    written = await insert_signal(row)

    return IngestResult(
        run_id=run_id,
        signal_id=signal_id,
        node_id=payload.node_id,
        status=gate_status.value,
        gates=gates,
        written=written,
    )

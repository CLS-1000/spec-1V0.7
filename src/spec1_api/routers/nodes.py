"""Nodes router — GET /api/v1/nodes/{node_id}/signal

Returns a NodeTooltipPayload for the Portland Political Web visualization.
Each node maps to a real political actor; signals are fetched live from the
political_signals table and surfaced as tooltip data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from spec1_api.db.signals import get_latest_signal_for_node
from spec1_api.schemas.node_signal import (
    GateScores,
    GateStatus,
    NodeTooltipPayload,
    SignalRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nodes", tags=["nodes"])

# ── Node registry — all 34 Portland Political Web nodes ──────────────────────

NODE_REGISTRY: dict[str, dict] = {
    "wilson":       {"label": "Mayor Keith Wilson",             "role": "EXECUTIVE"},
    "city_admin":   {"label": "City Administrator",             "role": "ADMINISTRATION"},
    "auditor":      {"label": "City Auditor",                   "role": "WATCHDOG"},
    "pirtle":       {"label": "Councilor Mitch Pirtle",         "role": "LEGISLATIVE"},
    "clark":        {"label": "Councilor Eric Clark",           "role": "LEGISLATIVE"},
    "avalos":       {"label": "Councilor Roberto Avalos",       "role": "LEGISLATIVE"},
    "dunphy":       {"label": "Councilor Olivia Dunphy",        "role": "LEGISLATIVE"},
    "lsmith":       {"label": "Councilor LaVonne Smith",        "role": "LEGISLATIVE"},
    "kanal":        {"label": "Councilor Candace Avalos-Kanal", "role": "LEGISLATIVE"},
    "ryan":         {"label": "Councilor Steve Ryan",           "role": "LEGISLATIVE"},
    "koyama":       {"label": "Councilor Samantha Koyama",      "role": "LEGISLATIVE"},
    "morillo":      {"label": "Councilor Angelita Morillo",     "role": "LEGISLATIVE"},
    "novick":       {"label": "Steve Novick (Former Official)", "role": "COMMENTATOR"},
    "green":        {"label": "Councilor Loretta Green",        "role": "LEGISLATIVE"},
    "zimmerman":    {"label": "Councilor Dan Zimmerman",        "role": "LEGISLATIVE"},
    "peacock":      {"label": "Councilor Julia Peacock",        "role": "LEGISLATIVE"},
    "vega":         {"label": "Councilor Maria Vega",           "role": "LEGISLATIVE"},
    "county":       {"label": "Multnomah County",               "role": "REGIONAL_GOVERNMENT"},
    "metro":        {"label": "Metro Regional Government",      "role": "REGIONAL_GOVERNMENT"},
    "kotek":        {"label": "Governor Tina Kotek",            "role": "STATE_EXECUTIVE"},
    "ore_leg":      {"label": "Oregon Legislature",             "role": "STATE_LEGISLATIVE"},
    "homelessness": {"label": "Joint Office of Homeless Services", "role": "SERVICES"},
    "housing":      {"label": "Portland Housing Bureau",        "role": "SERVICES"},
    "budget":       {"label": "City Budget Office",             "role": "ADMINISTRATION"},
    "charter":      {"label": "Charter Implementation",         "role": "ADMINISTRATION"},
    "rcv":          {"label": "Ranked Choice Voting",           "role": "ADMINISTRATION"},
    "police":       {"label": "Portland Police Bureau",         "role": "LAW_ENFORCEMENT"},
    "ethics":       {"label": "City Ethics Commission",         "role": "WATCHDOG"},
    "business_tax": {"label": "Business Tax Division",          "role": "ADMINISTRATION"},
    "pba":          {"label": "Portland Business Alliance",     "role": "ADVOCACY"},
    "psr":          {"label": "Portland Street Response",       "role": "SERVICES"},
    "fire_bds":     {"label": "Portland Fire & Rescue",         "role": "SERVICES"},
    "irp":          {"label": "Impact Reduction Program",       "role": "SERVICES"},
    "lwv":          {"label": "League of Women Voters",         "role": "CIVIC"},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _age_hours(published_at: datetime) -> float:
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - published_at).total_seconds() / 3600


def _freshness(age_h: float) -> str:
    if age_h < 6:
        return "LIVE"
    if age_h < 24:
        return "RECENT"
    return "STALE"


def _row_to_signal(row: dict) -> SignalRecord:
    pub = _parse_dt(row["published_at"])
    ret = _parse_dt(row["retrieved_at"])
    age_h = _age_hours(pub)
    tags = json.loads(row.get("tags") or "[]")
    return SignalRecord(
        node_id=row["node_id"],
        run_id=row["run_id"],
        signal_id=row["signal_id"],
        headline=row["headline"],
        summary=row["summary"],
        source_url=row["source_url"],
        source_domain=row["source_domain"],
        published_at=pub,
        retrieved_at=ret,
        gates=GateScores(
            credibility=row["gate_credibility"],
            volume=row["gate_volume"],
            velocity=row["gate_velocity"],
            novelty=row["gate_novelty"],
        ),
        gate_status=GateStatus(row["gate_status"]),
        signal_age_hours=round(age_h, 2),
        freshness_label=_freshness(age_h),
        analyst_voice=row.get("analyst_voice"),
        conflict_score=row.get("conflict_score"),
        tags=tags,
    )


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/{node_id}/signal", response_model=NodeTooltipPayload)
async def get_node_signal(node_id: str) -> NodeTooltipPayload:
    """Return the latest PASS signal for *node_id*, or a stale payload if none exists."""
    if node_id not in NODE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown node: {node_id!r}")

    meta = NODE_REGISTRY[node_id]
    row = await get_latest_signal_for_node(node_id)

    if row is None:
        return NodeTooltipPayload(
            node_id=node_id,
            label=meta["label"],
            role=meta["role"],
            signal=None,
            stale=True,
            last_updated=None,
        )

    signal = _row_to_signal(row)
    # Compute age directly from published_at — not from the rounded signal_age_hours
    # field — to avoid a rounding error flipping the stale flag at the 48h boundary.
    precise_age_h = _age_hours(signal.published_at)

    return NodeTooltipPayload(
        node_id=node_id,
        label=meta["label"],
        role=meta["role"],
        signal=signal,
        stale=precise_age_h > 48,
        last_updated=signal.published_at,
    )

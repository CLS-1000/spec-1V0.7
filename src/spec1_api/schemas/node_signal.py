"""Pydantic schemas for the Portland Political Web signal loop."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from spec1_core.signal.gates import GATE_THRESHOLD


class GateScores(BaseModel):
    credibility: float
    volume: float
    velocity: float
    novelty: float

    def all_pass(self) -> bool:
        """Return True if every gate score is strictly greater than GATE_THRESHOLD."""
        return (
            self.credibility > GATE_THRESHOLD
            and self.volume > GATE_THRESHOLD
            and self.velocity > GATE_THRESHOLD
            and self.novelty > GATE_THRESHOLD
        )


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class SignalRecord(BaseModel):
    node_id: str
    run_id: str
    signal_id: str
    headline: str
    summary: str
    source_url: str
    source_domain: str
    published_at: datetime
    retrieved_at: datetime
    gates: GateScores
    gate_status: GateStatus
    signal_age_hours: float
    freshness_label: str  # LIVE | RECENT | STALE
    analyst_voice: Optional[str] = None
    conflict_score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class NodeTooltipPayload(BaseModel):
    node_id: str
    label: str
    role: str
    signal: Optional[SignalRecord] = None
    stale: bool
    last_updated: Optional[datetime] = None


class CrawlerPayload(BaseModel):
    node_id: str
    headline: str
    body: str
    source_url: str
    source_domain: str
    published_at: datetime
    analyst_voice: Optional[str] = None
    conflict_score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class IngestResult(BaseModel):
    run_id: str
    signal_id: str
    node_id: str
    status: str  # PASS | FAIL
    gates: GateScores
    written: bool

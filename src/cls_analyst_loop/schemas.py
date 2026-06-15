# @domain:   spec-1
# @module:   schemas
# @loc:      _SCRATCH
# @status:   drafting
# @depends:  cls_db

"""Data schemas for cls_analyst_loop — analyst workflow chain of custody."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AnalystCase:
    """A case file tracking one lead from dispatch to verdict."""

    case_id: str
    run_id: str
    lead_id: str
    lead_text: str
    feed_prompt: str
    analyst_id: str
    created_at: datetime = field(default_factory=_now)
    schema_version: int = 1

    @classmethod
    def make_id(cls, lead_id: str, analyst_id: str, created_at: datetime | str) -> str:
        ts = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
        raw = f"{lead_id}::{analyst_id}::{ts}"
        return "case_" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "run_id": self.run_id,
            "lead_id": self.lead_id,
            "lead_text": self.lead_text,
            "feed_prompt": self.feed_prompt,
            "analyst_id": self.analyst_id,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else str(self.created_at),
            "schema_version": self.schema_version,
        }


@dataclass
class AnalystOutput:
    """An analyst's report submitted for a case."""

    output_id: str
    case_id: str
    raw_output: str
    source_data: str
    submitted_at: datetime = field(default_factory=_now)
    schema_version: int = 1

    @classmethod
    def make_id(cls, case_id: str, submitted_at: datetime | str) -> str:
        ts = submitted_at.isoformat() if isinstance(submitted_at, datetime) else str(submitted_at)
        raw = f"{case_id}::{ts}"
        return "output_" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "output_id": self.output_id,
            "case_id": self.case_id,
            "raw_output": self.raw_output,
            "source_data": self.source_data,
            "submitted_at": self.submitted_at.isoformat()
            if isinstance(self.submitted_at, datetime)
            else str(self.submitted_at),
            "schema_version": self.schema_version,
        }


@dataclass
class AuditResult:
    """An LLM audit of an analyst's output."""

    audit_id: str
    output_id: str
    audit_llm: str
    audit_prompt: str
    claims_confirmed: int
    claims_flagged: int
    claims_dropped: int
    audit_output: str
    confidence: float
    audited_at: datetime = field(default_factory=_now)
    schema_version: int = 1

    @classmethod
    def make_id(cls, output_id: str, audit_llm: str, audited_at: datetime | str) -> str:
        ts = audited_at.isoformat() if isinstance(audited_at, datetime) else str(audited_at)
        raw = f"{output_id}::{audit_llm}::{ts}"
        return "audit_" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "output_id": self.output_id,
            "audit_llm": self.audit_llm,
            "audit_prompt": self.audit_prompt,
            "claims_confirmed": self.claims_confirmed,
            "claims_flagged": self.claims_flagged,
            "claims_dropped": self.claims_dropped,
            "audit_output": self.audit_output,
            "confidence": self.confidence,
            "audited_at": self.audited_at.isoformat()
            if isinstance(self.audited_at, datetime)
            else str(self.audited_at),
            "schema_version": self.schema_version,
        }


AnalystVerdictKind = Literal["confirmed", "partial", "flagged", "rejected"]
VALID_VERDICTS: frozenset[str] = frozenset({"confirmed", "partial", "flagged", "rejected"})


@dataclass
class AnalystVerdict:
    """Human verdict on an analyst's output — routes to publication or archive."""

    verdict_id: str
    case_id: str
    output_id: str
    audit_id: Optional[str]
    kind: AnalystVerdictKind
    reviewer: str
    notes: str
    published: bool
    filed_at: datetime = field(default_factory=_now)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.kind not in VALID_VERDICTS:
            raise ValueError(
                f"kind must be one of {sorted(VALID_VERDICTS)}, got {self.kind!r}"
            )

    @classmethod
    def make_id(cls, case_id: str, reviewer: str, filed_at: datetime | str) -> str:
        ts = filed_at.isoformat() if isinstance(filed_at, datetime) else str(filed_at)
        raw = f"{case_id}::{reviewer}::{ts}"
        return "verdict_" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "verdict_id": self.verdict_id,
            "case_id": self.case_id,
            "output_id": self.output_id,
            "audit_id": self.audit_id,
            "kind": self.kind,
            "reviewer": self.reviewer,
            "notes": self.notes,
            "published": self.published,
            "filed_at": self.filed_at.isoformat()
            if isinstance(self.filed_at, datetime)
            else str(self.filed_at),
            "schema_version": self.schema_version,
        }

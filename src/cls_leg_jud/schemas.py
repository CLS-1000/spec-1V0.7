"""Schemas for Legislative & Judicial Desk."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


SECTION_KINDS = [
    "executive_summary",
    "federal_members",
    "federal_lobbying",
    "judicial",
    "state_leg",
    "stated_purpose_vs_beneficiary",
    "geopolitical_context",
    "story_leads",
]

# Stable — do not rename; PDF (ReportLab) and X publisher depend on these exact strings
SECTION_TITLES: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "federal_members": "Federal — Members, Votes, Hearings",
    "federal_lobbying": "Federal — Lobbying & Disclosure Watch",
    "judicial": "Judicial Activity & Disclosures",
    "state_leg": "State Legislatures & Elected Officials",
    "stated_purpose_vs_beneficiary": "Stated Purpose vs Observed Beneficiary",
    "geopolitical_context": "Geopolitical Context",
    "story_leads": "Story Leads",
}


@dataclass
class LegJudSection:
    kind: str
    title: str   # from SECTION_TITLES
    body: str    # synthesised content or "NO SIGNAL THIS CYCLE"
    record_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "record_ids": self.record_ids,
        }


@dataclass
class LegJudBrief:
    brief_id: str
    run_id: str
    date: str              # ISO "YYYY-MM-DD"
    sections: list[LegJudSection] = field(default_factory=list)
    total_records: int = 0
    eligible_records: int = 0
    produced_at: datetime = field(default_factory=_now)

    @classmethod
    def make_id(cls, run_id: str) -> str:
        return "lj_" + hashlib.sha256(run_id.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "run_id": self.run_id,
            "date": self.date,
            "sections": [s.to_dict() for s in self.sections],
            "total_records": self.total_records,
            "eligible_records": self.eligible_records,
            "produced_at": self.produced_at.isoformat(),
        }

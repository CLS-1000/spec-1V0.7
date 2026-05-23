"""Data schemas for cls_osint."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_id(prefix: str, *parts: str) -> str:
    raw = ":".join(parts)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


@dataclass
class OSINTRecord:
    """Generic OSINT record produced by any adapter."""

    record_id: str
    source_type: str       # "fara" | "congressional" | "narrative" | "rss"
    source_name: str
    content: str
    url: str
    collected_at: datetime = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "content": self.content,
            "url": self.url,
            "collected_at": self.collected_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class FaraRecord:
    """A Foreign Agents Registration Act filing."""

    record_id: str
    registrant: str              # Entity registering as foreign agent
    foreign_principal: str       # Foreign government / entity being represented
    country: str
    activities: list[str]        # Described activities
    filed_at: datetime
    doc_url: str
    registration_number: str = ""
    status: str = "ACTIVE"       # "active" | "terminated"
    metadata: dict = field(default_factory=dict)

    @classmethod
    def make_id(cls, registrant: str, foreign_principal: str, filed_at: str) -> str:
        return _make_id("fara", registrant, foreign_principal, filed_at)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "registrant": self.registrant,
            "foreign_principal": self.foreign_principal,
            "country": self.country,
            "activities": self.activities,
            "filed_at": self.filed_at.isoformat() if isinstance(self.filed_at, datetime) else str(self.filed_at),
            "doc_url": self.doc_url,
            "registration_number": self.registration_number,
            "status": self.status,
            "metadata": self.metadata,
        }

    def to_osint_record(self) -> OSINTRecord:
        summary = (
            f"{self.registrant} registered as foreign agent for {self.foreign_principal} "
            f"({self.country}). Activities: {'; '.join(self.activities)}."
        )
        return OSINTRecord(
            record_id=self.record_id,
            source_type="FARA",
            source_name="fara_db",
            content=summary,
            url=self.doc_url,
            collected_at=_now(),
            metadata=self.to_dict(),
        )


@dataclass
class CongressRecord:
    """A US Congressional record (bill, hearing, or resolution)."""

    record_id: str
    record_type: str         # BILL | RESOLUTION | HEARING | AMENDMENT
    bill_id: str             # e.g. "H.R.1234" or "S.567"
    title: str
    sponsor: str
    chamber: str             # HOUSE | SENATE
    status: str              # INTRODUCED | PASSED_HOUSE | PASSED_SENATE | ENACTED | FAILED
    date: datetime
    summary: str
    url: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def make_id(cls, bill_id: str, date: str) -> str:
        return _make_id("congress", bill_id, date)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "record_type": self.record_type,
            "bill_id": self.bill_id,
            "title": self.title,
            "sponsor": self.sponsor,
            "chamber": self.chamber,
            "status": self.status,
            "date": self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            "summary": self.summary,
            "url": self.url,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def to_osint_record(self) -> OSINTRecord:
        content = f"{self.bill_id}: {self.title}. Sponsor: {self.sponsor}. Status: {self.status}. {self.summary}"
        return OSINTRecord(
            record_id=self.record_id,
            source_type="CONGRESSIONAL",
            source_name="congress_gov",
            content=content,
            url=self.url,
            collected_at=_now(),
            metadata=self.to_dict(),
        )


@dataclass
class NarrativeRecord:
    """A detected influence or narrative pattern across sources."""

    record_id: str
    theme: str               # Short label, e.g. "China-Taiwan escalation"
    description: str         # Human-readable summary
    amplifiers: list[str]    # Accounts / outlets amplifying
    reach_score: float       # 0–1 estimated reach
    sentiment: str           # POSITIVE | NEGATIVE | NEUTRAL | MIXED
    source_urls: list[str]
    detected_at: datetime = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def make_id(cls, theme: str, detected_at: str) -> str:
        return _make_id("narrative", theme, detected_at)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "theme": self.theme,
            "description": self.description,
            "amplifiers": self.amplifiers,
            "reach_score": self.reach_score,
            "sentiment": self.sentiment,
            "source_urls": self.source_urls,
            "detected_at": self.detected_at.isoformat() if isinstance(self.detected_at, datetime) else str(self.detected_at),
            "metadata": self.metadata,
        }

    def to_osint_record(self) -> OSINTRecord:
        amplifier_str = ", ".join(self.amplifiers[:5])
        content = (
            f"Narrative detected: {self.theme}. {self.description} "
            f"Amplifiers: {amplifier_str}. Reach score: {self.reach_score:.2f}."
        )
        return OSINTRecord(
            record_id=self.record_id,
            source_type="NARRATIVE",
            source_name="narrative_tracker",
            content=content,
            url=self.source_urls[0] if self.source_urls else "",
            collected_at=self.detected_at,
            metadata=self.to_dict(),
        )


@dataclass
class JudicialRecord:
    """A federal judicial record (ruling, recusal, financial disclosure, gift, speaking engagement)."""

    record_id: str
    judge: str
    court: str
    district: str
    action_type: str          # "ruling" | "recusal" | "disclosure" | "gift" | "speaking_engagement"
    case_ref: str
    ruling_summary: str
    disclosed_ties: list[str]
    recusal_basis: str
    gift_amount: float
    engagement_sponsor: str
    filed_at: str             # ISO date string
    source_url: str
    metadata: dict = field(default_factory=dict)

    @classmethod
    def make_id(cls, judge: str, action_type: str, filed_at: str) -> str:
        return _make_id("judicial", judge, action_type, filed_at)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "judge": self.judge,
            "court": self.court,
            "district": self.district,
            "action_type": self.action_type,
            "case_ref": self.case_ref,
            "ruling_summary": self.ruling_summary,
            "disclosed_ties": self.disclosed_ties,
            "recusal_basis": self.recusal_basis,
            "gift_amount": self.gift_amount,
            "engagement_sponsor": self.engagement_sponsor,
            "filed_at": self.filed_at,
            "source_url": self.source_url,
            "metadata": self.metadata,
        }

    def to_osint_record(self) -> OSINTRecord:
        ties_str = "; ".join(self.disclosed_ties) if self.disclosed_ties else "none"
        content = (
            f"Judge {self.judge} ({self.court}, {self.district}): {self.action_type} — "
            f"{self.case_ref}. {self.ruling_summary} "
            f"Disclosed ties: {ties_str}."
        )
        return OSINTRecord(
            record_id=self.record_id,
            source_type="JUDICIAL",
            source_name="federal_courts",
            content=content,
            url=self.source_url,
            collected_at=_now(),
            metadata=self.to_dict(),
        )


@dataclass
class StateLegRecord:
    """A state legislative record with disclosure-regime tracking."""

    record_id: str
    state: str
    bill_id: str
    title: str
    sponsor: str
    chamber: str              # "HOUSE" | "SENATE" | "JOINT"
    status: str               # "INTRODUCED" | "PASSED_HOUSE" | "PASSED_SENATE" | "ENACTED" | "FAILED"
    summary: str
    disclosure_regime: str    # "FULL" | "PARTIAL" | "NONE"
    disclosure_gap: bool
    filed_at: str             # ISO date string
    source_url: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def make_id(cls, state: str, bill_id: str, filed_at: str) -> str:
        return _make_id("state_leg", state, bill_id, filed_at)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "state": self.state,
            "bill_id": self.bill_id,
            "title": self.title,
            "sponsor": self.sponsor,
            "chamber": self.chamber,
            "status": self.status,
            "summary": self.summary,
            "disclosure_regime": self.disclosure_regime,
            "disclosure_gap": self.disclosure_gap,
            "filed_at": self.filed_at,
            "source_url": self.source_url,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def to_osint_record(self) -> OSINTRecord:
        tag_str = ", ".join(self.tags) if self.tags else ""
        gap_note = f" DISCLOSURE GAP: {self.state}." if self.disclosure_gap else ""
        content = (
            f"{self.bill_id} ({self.state}): {self.title}. Sponsor: {self.sponsor}. "
            f"Chamber: {self.chamber}. Status: {self.status}. {self.summary}"
            f"{gap_note} Disclosure regime: {self.disclosure_regime}. "
            f"Tags: {tag_str}."
        )
        return OSINTRecord(
            record_id=self.record_id,
            source_type="STATE_LEG",
            source_name="state_legislature",
            content=content,
            url=self.source_url,
            collected_at=_now(),
            metadata=self.to_dict(),
        )

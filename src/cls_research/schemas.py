# @domain:   product
# @module:   schemas
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Data schemas for cls_research (Research Mode).

Mirrors the shape of the other cls_* schema modules (cls_leads, cls_psyop,
cls_world_brief): plain dataclasses with explicit ``to_dict`` / ``from_dict``
round-trips, no I/O, no scoring. Persistence lives in ``store.py`` and
``topics.py``; deterministic logic lives in ``expansion.py``,
``collector.py``, and ``dossier.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from spec1_labels import RESEARCH_STATUS_DRAFT


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def slugify(name: str) -> str:
    """Deterministic slug for a topic name — same name always yields the same id.

    Unlike signal/case IDs (random, since they identify single events), topic
    profiles are analyst-authored and stable, so their id is derived from the
    name rather than generated. This keeps ``research/topics/<id>.json`` and
    ``research/dossiers/<id>.jsonl`` filenames legible and grep-able.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "topic"


@dataclass
class TopicProfile:
    """Analyst-defined research topic — the input to Research Mode.

    Fields map directly to the deterministic expansion and collection rules
    in ``expansion.py`` / ``collector.py``:
      - keywords/entities/geographies are combined (not ranked) to broaden
        coverage.
      - aliases let an analyst declare known synonyms ("DPRK" -> "North
        Korea") without the system guessing at them.
      - source_classes should use the canonical SOURCE_* constants from
        spec1_labels (e.g. SOURCE_RSS, SOURCE_FARA) where the source type
        is already collectible by Research Mode; classes that aren't yet
        wired into the collector are surfaced as collection gaps rather
        than silently ignored (see dossier.py).
      - exclusions are a deterministic negative filter applied verbatim
        (case-insensitive substring match) — never a learned filter.
    """

    topic_id: str
    name: str
    core_question: str
    subquestions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    geographies: list[str] = field(default_factory=list)
    time_horizon_days: int = 90
    source_classes: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    analyst_notes: str = ""
    aliases: dict[str, list[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def make_id(cls, name: str) -> str:
        return f"topic_{slugify(name)}"

    @classmethod
    def new(cls, name: str, core_question: str, **kwargs) -> "TopicProfile":
        """Convenience constructor that derives topic_id from name."""
        return cls(topic_id=cls.make_id(name), name=name, core_question=core_question, **kwargs)

    def to_dict(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "name": self.name,
            "core_question": self.core_question,
            "subquestions": list(self.subquestions),
            "keywords": list(self.keywords),
            "entities": list(self.entities),
            "geographies": list(self.geographies),
            "time_horizon_days": self.time_horizon_days,
            "source_classes": list(self.source_classes),
            "exclusions": list(self.exclusions),
            "analyst_notes": self.analyst_notes,
            "aliases": dict(self.aliases),
            "created_at": _iso(self.created_at),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TopicProfile":
        return cls(
            topic_id=d.get("topic_id") or cls.make_id(d["name"]),
            name=d["name"],
            core_question=d["core_question"],
            subquestions=list(d.get("subquestions", [])),
            keywords=list(d.get("keywords", [])),
            entities=list(d.get("entities", [])),
            geographies=list(d.get("geographies", [])),
            time_horizon_days=int(d.get("time_horizon_days", 90)),
            source_classes=list(d.get("source_classes", [])),
            exclusions=list(d.get("exclusions", [])),
            analyst_notes=d.get("analyst_notes", ""),
            aliases=dict(d.get("aliases", {})),
            created_at=_parse_dt(d.get("created_at")) or _now(),
            metadata=dict(d.get("metadata", {})),
        )


@dataclass
class ExpandedTerm:
    """One deterministic query-expansion result, with its derivation rule.

    ``rule`` and ``derived_from`` exist so expansion is auditable — every
    term in a dossier can be traced back to the exact profile field(s) and
    rule that produced it. No term carries a weight or rank.
    """

    term: str
    rule: str                          # e.g. "keyword" | "alias" | "keyword_x_entity" | "keyword_x_geography" | "subquestion"
    derived_from: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"term": self.term, "rule": self.rule, "derived_from": list(self.derived_from)}

    @classmethod
    def from_dict(cls, d: dict) -> "ExpandedTerm":
        return cls(term=d["term"], rule=d["rule"], derived_from=list(d.get("derived_from", [])))


@dataclass
class CollectedItem:
    """A harvested signal that matched the topic's expanded terms.

    ``credibility_annotation`` reuses the existing domain-credibility table
    (spec1_core.signal.gates) purely as analyst context — it is never used
    to filter or rank collected items.
    """

    item_id: str
    signal_id: str
    source: str
    source_type: str
    url: str
    title: str
    excerpt: str
    published_at: Optional[datetime]
    matched_terms: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    credibility_annotation: Optional[float] = None
    collected_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "signal_id": self.signal_id,
            "source": self.source,
            "source_type": self.source_type,
            "url": self.url,
            "title": self.title,
            "excerpt": self.excerpt,
            "published_at": _iso(self.published_at),
            "matched_terms": list(self.matched_terms),
            "matched_rules": list(self.matched_rules),
            "credibility_annotation": self.credibility_annotation,
            "collected_at": _iso(self.collected_at),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CollectedItem":
        return cls(
            item_id=d["item_id"],
            signal_id=d["signal_id"],
            source=d["source"],
            source_type=d["source_type"],
            url=d["url"],
            title=d["title"],
            excerpt=d.get("excerpt", ""),
            published_at=_parse_dt(d.get("published_at")),
            matched_terms=list(d.get("matched_terms", [])),
            matched_rules=list(d.get("matched_rules", [])),
            credibility_annotation=d.get("credibility_annotation"),
            collected_at=_parse_dt(d.get("collected_at")) or _now(),
        )


@dataclass
class ResearchArtifact:
    """A persistent research dossier — one version of the accumulated
    research record for a topic.

    Each call to ``pipeline.run_research`` for a topic appends a new,
    incrementing ``version`` to the topic's JSONL store (append-only, like
    every other SPEC-1 store). The dossier separates topic definition,
    collected evidence, deterministic findings, open gaps, and provenance
    into distinct sections so each can be audited independently.
    """

    dossier_id: str
    topic_id: str
    topic_name: str
    version: int
    run_id: str
    generated_at: datetime
    topic_definition: dict
    expansion_terms: list[dict]
    collected_items: list[dict]
    notable_findings: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    status: str = RESEARCH_STATUS_DRAFT

    @classmethod
    def make_id(cls, topic_id: str, version: int) -> str:
        return f"dossier_{topic_id}_v{version}"

    def to_dict(self) -> dict:
        return {
            "dossier_id": self.dossier_id,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "version": self.version,
            "run_id": self.run_id,
            "generated_at": _iso(self.generated_at),
            "topic_definition": self.topic_definition,
            "expansion_terms": self.expansion_terms,
            "collected_items": self.collected_items,
            "notable_findings": list(self.notable_findings),
            "unresolved_questions": list(self.unresolved_questions),
            "provenance": self.provenance,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResearchArtifact":
        return cls(
            dossier_id=d["dossier_id"],
            topic_id=d["topic_id"],
            topic_name=d["topic_name"],
            version=int(d["version"]),
            run_id=d.get("run_id", ""),
            generated_at=_parse_dt(d.get("generated_at")) or _now(),
            topic_definition=dict(d.get("topic_definition", {})),
            expansion_terms=list(d.get("expansion_terms", [])),
            collected_items=list(d.get("collected_items", [])),
            notable_findings=list(d.get("notable_findings", [])),
            unresolved_questions=list(d.get("unresolved_questions", [])),
            provenance=dict(d.get("provenance", {})),
            status=d.get("status", RESEARCH_STATUS_DRAFT),
        )

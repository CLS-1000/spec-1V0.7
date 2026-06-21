# @domain:   product
# @module:   collector
# @loc:      gh_main
# @status:   stable
# @depends:  spec1_core/signal

"""Research Mode collector — reuse, not duplicate.

This module deliberately does not re-implement RSS fetching or text
cleaning. It calls the same harvester and parser used by Signal Mode
(``spec1_core.signal.harvester.harvest_all`` / ``...parser.parse_signal``)
and applies a different, deterministic selection step on top: does this
parsed signal contain any of the topic's expanded terms?

What is intentionally NOT here:
  - the 4-gate credibility/volume/velocity/novelty filter — that gate set
    answers "is this worth surfacing today", which is a Signal Mode
    question. Research Mode's job is broad topic coverage, not daily
    triage, so passing/failing those gates is not part of collection.
  - any ranking of matched items — matches are kept in harvest order.

Domain credibility (``spec1_core.signal.gates.score_credibility``) is
reused, but only to *annotate* each collected item for analyst context —
never to drop or reorder items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from spec1_core.core import ids, logging_utils
from spec1_core.schemas.models import ParsedSignal, Signal
from spec1_core.signal.gates import score_credibility
from spec1_core.signal.harvester import DEFAULT_FEEDS, harvest_all
from spec1_core.signal.parser import parse_signal

from cls_research.expansion import base_match_terms
from cls_research.schemas import CollectedItem, ExpandedTerm, TopicProfile

logger = logging_utils.get_logger(__name__)


@dataclass
class CollectionResult:
    """Output of one collection pass: matched items plus an explicit
    accounting of what was scanned and why items were dropped."""

    items: list[CollectedItem] = field(default_factory=list)
    signals_scanned: int = 0
    signals_outside_horizon: int = 0
    signals_excluded: int = 0
    harvest_errors: dict = field(default_factory=dict)
    sources_scanned: list[str] = field(default_factory=list)


def _haystack(signal: Signal, parsed: ParsedSignal) -> str:
    """Build the lowercase text a term is matched against."""
    parts = [
        parsed.cleaned_text or "",
        signal.source or "",
        signal.author or "",
        " ".join(parsed.keywords),
        " ".join(parsed.entities),
    ]
    return " ".join(parts).lower()


def _within_horizon(published_at: datetime, horizon_days: int, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return (now - published_at) <= timedelta(days=horizon_days)


def _is_excluded(haystack: str, exclusions: list[str]) -> bool:
    return any(_x.lower().strip() in haystack for _x in exclusions if _x.strip())


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def match_terms(haystack: str, terms: list[ExpandedTerm]) -> tuple[list[str], list[str]]:
    """Return (matched_term_strings, matched_rule_tags) for one haystack.

    Pure substring containment, case-insensitive — the same matching
    primitive already used by ``workspace.tracker._signal_matches_case``.
    No fuzzy matching, no scoring.
    """
    matched_terms: list[str] = []
    matched_rules: list[str] = []
    for t in terms:
        if t.term and t.term in haystack:
            matched_terms.append(t.term)
            matched_rules.append(t.rule)
    return matched_terms, matched_rules


def collect_for_topic(
    profile: TopicProfile,
    expansion: list[ExpandedTerm],
    feeds: Optional[dict[str, str]] = None,
    signals: Optional[list[Signal]] = None,
    run_id: str = "",
    environment: str = "research",
) -> CollectionResult:
    """Collect signals matching a topic's expanded terms.

    Args:
        profile: the topic being researched (used for time_horizon_days
            and exclusions).
        expansion: output of ``expansion.expand_topic(profile)``.
        feeds: optional feed name->url map; defaults to the same
            DEFAULT_FEEDS Signal Mode harvests. Ignored if ``signals`` is
            given.
        signals: optional pre-harvested Signal list. When provided, no
            network call is made — this lets Research Mode reuse signals
            already harvested in the same cycle (or in tests), instead of
            re-fetching the same feeds twice.
        run_id: propagated onto harvested signals for traceability.
        environment: propagated onto harvested signals; defaults to
            "research" so Research Mode signals are distinguishable from
            "production" Signal Mode signals if the two share a store.

    Returns:
        CollectionResult with matched items and an explicit drop accounting.
    """
    match_terms_set = base_match_terms(expansion)

    harvest_errors: dict = {}
    if signals is None:
        result = harvest_all(feeds=feeds or DEFAULT_FEEDS, run_id=run_id, environment=environment)
        signals = result["signals"]
        harvest_errors = result["errors"]

    now = datetime.now(timezone.utc)
    items: list[CollectedItem] = []
    outside_horizon = 0
    excluded = 0
    sources: set[str] = set()

    for sig in signals:
        sources.add(sig.source)

        if not _within_horizon(sig.published_at, profile.time_horizon_days, now=now):
            outside_horizon += 1
            continue

        parsed = parse_signal(sig)
        haystack = _haystack(sig, parsed)

        if profile.exclusions and _is_excluded(haystack, profile.exclusions):
            excluded += 1
            continue

        matched_terms, matched_rules = match_terms(haystack, match_terms_set)
        if not matched_terms:
            continue

        domain = _domain_of(sig.url)
        items.append(
            CollectedItem(
                item_id=ids.deterministic_id(f"{profile.topic_id}:{sig.signal_id}"),
                signal_id=sig.signal_id,
                source=sig.source,
                source_type=sig.source_type,
                url=sig.url,
                title=(parsed.cleaned_text or "")[:120],
                excerpt=(parsed.cleaned_text or "")[:400],
                published_at=sig.published_at,
                matched_terms=sorted(set(matched_terms)),
                matched_rules=sorted(set(matched_rules)),
                credibility_annotation=score_credibility(domain) if domain else None,
            )
        )

    logger.info(
        f"research_collected: topic_id={profile.topic_id}, scanned={len(signals)}, "
        f"matched={len(items)}, outside_horizon={outside_horizon}, excluded={excluded}"
    )

    return CollectionResult(
        items=items,
        signals_scanned=len(signals),
        signals_outside_horizon=outside_horizon,
        signals_excluded=excluded,
        harvest_errors=harvest_errors,
        sources_scanned=sorted(sources),
    )

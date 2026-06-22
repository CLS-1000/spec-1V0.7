# @domain:   product
# @module:   dossier
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Assembles a ResearchArtifact (dossier) from a topic, its expansion, and
one collection pass — optionally against the topic's prior dossier version.

Two deterministic, rule-based steps happen here, and both are documented
in full because "deterministic" only means something if the rule is
legible:

1. **Collection-gap detection** (-> ``unresolved_questions``)
   - For each ``profile.subquestions`` entry: tokenise it into words (the
     same stopword list as the existing signal parser), then check whether
     ANY of those words appears among the ``matched_terms`` of any
     collected item. If none do, the subquestion is flagged as a gap —
     evidence exists for the topic overall, but not for that specific
     subquestion.
   - For each ``profile.source_classes`` entry that is not SOURCE_RSS: the
     collector currently only harvests RSS, so any other declared source
     class is flagged as a gap explaining *why* (not yet wired in), rather
     than silently producing zero items for it.
   - If zero items were collected at all, a single top-level gap is added.

2. **Notable findings** (-> ``notable_findings``) are a diff against the
   topic's previous dossier version, not an LLM summary:
   - count of net-new items (by signal_id) since the prior version
   - any source name appearing in this collection that did not appear in
     the prior one
   - on the first run for a topic (no prior version), a single coverage
     line instead of a diff.

Nothing here ranks or classifies evidence — it only counts and compares.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from spec1_core.signal.parser import STOPWORDS
from spec1_labels import RESEARCH_GAP_MARKER, RESEARCH_STATUS_DRAFT, SOURCE_RSS

from cls_research.collector import CollectionResult
from cls_research.schemas import ExpandedTerm, ResearchArtifact, TopicProfile

_WORD_RE = re.compile(r"[a-z]+")

# Source classes the collector can actually act on today. Anything else in
# a profile's source_classes is a declared-but-unwired gap (see module
# docstring, point 1).
_COLLECTIBLE_SOURCE_CLASSES = {SOURCE_RSS}


def _tokenize(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in STOPWORDS}


def _detect_gaps(
    profile: TopicProfile,
    collection: CollectionResult,
) -> list[str]:
    gaps: list[str] = []

    if not collection.items:
        gaps.append(
            f"{RESEARCH_GAP_MARKER}: no items collected for core question "
            f"within the {profile.time_horizon_days}-day horizon."
        )

    all_matched_terms: set[str] = set()
    for item in collection.items:
        all_matched_terms.update(item.matched_terms)

    for sq in profile.subquestions:
        sq_tokens = _tokenize(sq)
        if sq_tokens and not (sq_tokens & all_matched_terms):
            gaps.append(f"{RESEARCH_GAP_MARKER}: no collected evidence addresses subquestion — \"{sq}\"")

    for source_class in profile.source_classes:
        if source_class not in _COLLECTIBLE_SOURCE_CLASSES:
            gaps.append(
                f"{RESEARCH_GAP_MARKER}: source_class '{source_class}' is declared in the topic "
                f"profile but is not yet wired into the Research Mode collector (RSS only in this "
                f"version) — see docs/research_mode.md."
            )

    for err_source, err_msg in collection.harvest_errors.items():
        gaps.append(f"{RESEARCH_GAP_MARKER}: harvest of source '{err_source}' failed — {err_msg}")

    return gaps


def _diff_findings(
    collection: CollectionResult,
    prior: Optional[ResearchArtifact],
) -> list[str]:
    if prior is None:
        return [
            f"Initial collection — {len(collection.items)} item(s) across "
            f"{len(collection.sources_scanned)} source(s); no prior dossier to compare against."
        ]

    prior_signal_ids = {it.get("signal_id") for it in prior.collected_items}
    prior_sources = {it.get("source") for it in prior.collected_items}

    new_items = [it for it in collection.items if it.signal_id not in prior_signal_ids]
    new_sources = sorted({it.source for it in collection.items} - prior_sources)

    findings: list[str] = [
        f"{len(new_items)} new item(s) since dossier v{prior.version} ({prior.generated_at})."
    ]
    for src in new_sources:
        findings.append(f"New source observed for this topic: {src}")

    return findings


def build_dossier(
    profile: TopicProfile,
    expansion: list[ExpandedTerm],
    collection: CollectionResult,
    run_id: str,
    prior: Optional[ResearchArtifact] = None,
) -> ResearchArtifact:
    """Assemble a ResearchArtifact from one collection pass.

    If ``prior`` is given (the topic's most recent stored dossier), the new
    items list is the running total: prior items are kept and de-duplicated
    against this pass's items by ``signal_id``, so the dossier accumulates
    across runs instead of only reflecting the latest cycle. This is what
    makes Research Mode "persistent" rather than a one-shot report.
    """
    version = (prior.version + 1) if prior is not None else 1

    items_by_signal_id: dict[str, dict] = {}
    if prior is not None:
        for it in prior.collected_items:
            items_by_signal_id[it["signal_id"]] = it
    for it in collection.items:
        items_by_signal_id[it.signal_id] = it.to_dict()

    gaps = _detect_gaps(profile, collection)
    findings = _diff_findings(collection, prior)

    provenance = {
        "sources_scanned": collection.sources_scanned,
        "signals_scanned_this_run": collection.signals_scanned,
        "signals_outside_horizon_this_run": collection.signals_outside_horizon,
        "signals_excluded_this_run": collection.signals_excluded,
        "harvest_errors_this_run": collection.harvest_errors,
        "time_horizon_days": profile.time_horizon_days,
        "prior_version": prior.version if prior is not None else None,
    }

    return ResearchArtifact(
        dossier_id=ResearchArtifact.make_id(profile.topic_id, version),
        topic_id=profile.topic_id,
        topic_name=profile.name,
        version=version,
        run_id=run_id,
        generated_at=datetime.now(timezone.utc),
        topic_definition=profile.to_dict(),
        expansion_terms=[t.to_dict() for t in expansion],
        collected_items=list(items_by_signal_id.values()),
        notable_findings=findings,
        unresolved_questions=gaps,
        provenance=provenance,
        status=RESEARCH_STATUS_DRAFT,
    )

# @domain:   product
# @module:   scorer
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Psyop scorer — scores text against known psyop patterns."""

from __future__ import annotations

import hashlib
from cls_psyop.patterns import PATTERNS, PsyopPattern
from cls_psyop.schemas import PsyopScore
from spec1_labels import PSYOP_HIGH_RISK, PSYOP_MEDIUM_RISK, PSYOP_LOW_RISK, PSYOP_CLEAN, THREAT_HIGH, THREAT_MEDIUM, THREAT_LOW


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _count_indicators(text: str, indicators: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for ind in indicators if ind.lower() in text_lower)


def _classify_score(score: float, matched_count: int) -> str:
    if score >= 0.6 or matched_count >= 3:
        return PSYOP_HIGH_RISK
    if score >= 0.3 or matched_count >= 2:
        return PSYOP_MEDIUM_RISK
    if score > 0 or matched_count >= 1:
        return PSYOP_LOW_RISK
    return PSYOP_CLEAN


def score_text(text: str, patterns: list[PsyopPattern] | None = None) -> PsyopScore:
    """Score a piece of text against psyop patterns.

    Returns a PsyopScore with matched patterns and a 0–1 likelihood score.
    """
    if patterns is None:
        patterns = PATTERNS

    text_hash = _hash_text(text)
    matched_ids: list[str] = []
    matched_names: list[str] = []
    matched_categories: set[str] = set()
    total_indicator_hits = 0

    for pattern in patterns:
        hits = _count_indicators(text, pattern.indicators)
        if hits >= 1:
            matched_ids.append(pattern.pattern_id)
            matched_names.append(pattern.name)
            matched_categories.add(pattern.category)
            # Weight by threat level
            weight = {THREAT_HIGH: 3, THREAT_MEDIUM: 2, THREAT_LOW: 1}.get(pattern.threat_level, 1)
            total_indicator_hits += hits * weight

    # Normalise to 0–1 (cap at 1.0)
    max_possible = len(patterns) * 3 * 2  # rough upper bound
    raw_score = total_indicator_hits / max_possible if max_possible > 0 else 0.0
    score = round(min(1.0, raw_score * 5.0), 3)  # scale up for sensitivity

    classification = _classify_score(score, len(matched_ids))

    return PsyopScore(
        score_id=PsyopScore.make_id(text_hash),
        text_hash=text_hash,
        text_excerpt=text[:200],
        patterns_matched=matched_ids,
        pattern_names=matched_names,
        score=score,
        classification=classification,
        threat_categories=sorted(matched_categories),
        metadata={"total_indicator_hits": total_indicator_hits},
    )


def score_records(records: list[dict]) -> list[PsyopScore]:
    """Score a list of record dicts; returns PsyopScore per record."""
    results: list[PsyopScore] = []
    for rec in records:
        text = rec.get("content", rec.get("text", rec.get("summary", "")))
        if not text:
            continue
        ps = score_text(str(text))
        ps.metadata["source_record_id"] = rec.get("record_id", rec.get("signal_id", ""))
        ps.metadata["source_name"] = rec.get("source_name", rec.get("source", ""))
        results.append(ps)
    return results


def filter_risky(scores: list[PsyopScore], min_classification: str = PSYOP_LOW_RISK) -> list[PsyopScore]:
    """Return only scores at or above the given risk threshold."""
    order = {PSYOP_CLEAN: 0, PSYOP_LOW_RISK: 1, PSYOP_MEDIUM_RISK: 2, PSYOP_HIGH_RISK: 3}
    threshold = order.get(min_classification, 1)
    return [s for s in scores if order.get(s.classification, 0) >= threshold]

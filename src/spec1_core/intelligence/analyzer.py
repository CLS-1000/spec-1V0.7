# @domain:   intelligence
# @module:   intelligence_analyzer
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Intelligence Analyzer.

Analyzes verified outcomes and produces IntelligenceRecord instances.
"""

from __future__ import annotations

import uuid

from spec1_core.schemas.models import (
    IntelligenceRecord,
    Investigation,
    Opportunity,
    Outcome,
    Signal,
)
from spec1_core.config.calibration import (
    SOURCE_CREDIBILITY,
    DEFAULT_CREDIBILITY,
    CLASSIFICATION_WEIGHTS,
    DEFAULT_ANALYST_WEIGHT,
    ANALYST_WEIGHTS,
)




def _extract_pattern(opportunity: Opportunity, investigation: Investigation) -> str:
    """Extract an intelligence pattern label."""
    priority = opportunity.priority
    gates = opportunity.gate_results
    gate_str = "+".join(k for k, v in gates.items() if v)

    hypothesis_snippet = investigation.hypothesis[:80].strip().rstrip(".")
    return f"[{priority}] {hypothesis_snippet} | gates={gate_str}"


def _calc_source_weight(signal: Signal) -> float:
    return SOURCE_CREDIBILITY.get(signal.source, DEFAULT_CREDIBILITY)


def _calc_analyst_weight(investigation: Investigation) -> float:
    leads = investigation.analyst_leads
    if not leads:
        return DEFAULT_ANALYST_WEIGHT
    weights = [ANALYST_WEIGHTS.get(lead, DEFAULT_ANALYST_WEIGHT) for lead in leads]
    return round(sum(weights) / len(weights), 4)


def analyze(
    opportunity: Opportunity,
    investigation: Investigation,
    outcome: Outcome,
    signal: Signal,
) -> IntelligenceRecord:
    """Produce an IntelligenceRecord from pipeline results."""
    source_weight = _calc_source_weight(signal)
    analyst_weight = _calc_analyst_weight(investigation)
    classification_weight = CLASSIFICATION_WEIGHTS.get(outcome.classification, 0.5)

    # Final confidence blends outcome confidence with weights
    final_confidence = round(
        outcome.confidence * 0.50
        + source_weight * 0.25
        + analyst_weight * 0.15
        + classification_weight * 0.10,
        4,
    )

    return IntelligenceRecord(
        record_id=f"rec-{uuid.uuid4().hex[:12]}",
        pattern=_extract_pattern(opportunity, investigation),
        classification=outcome.classification,
        confidence=min(final_confidence, 0.99),
        source_weight=source_weight,
        analyst_weight=analyst_weight,
    )

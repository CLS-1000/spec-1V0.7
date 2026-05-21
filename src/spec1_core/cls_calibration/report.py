from datetime import datetime
from .schemas import CalibrationProposal

def generate_report(proposal: CalibrationProposal) -> str:
    lines = [
        f"# SPEC-1 Calibration Report - {proposal.timestamp.strftime('%Y-%m-%d %H:%M')}",
        f"Proposal ID: {proposal.proposal_id}",
        f"Confidence: {proposal.confidence:.2f}",
        "",
        "## Current Thresholds",
        f"Credibility min: {proposal.current_thresholds.credibility_min}",
        f"Volume min: {proposal.current_thresholds.volume_min}",
        f"Novelty min hits: {proposal.current_thresholds.novelty_min_hits}",
        f"Composite STANDARD: {proposal.current_thresholds.composite_standard}",
        "",
        "## Proposed Changes",
    ]
    for k, v in proposal.proposed_thresholds.items():
        lines.append(f"  {k}: {v}")
    
    lines.extend([
        "",
        "## Metrics",
        f"Period: {proposal.metrics.period_days} days",
        f"Opportunities: {proposal.metrics.total_opportunities}",
        f"Positive verdict rate: {proposal.metrics.positive_verdict_rate:.1%}",
        f"Current daily volume: {proposal.metrics.current_volume}",
        "",
        "Suggested Actions:",
    ])
    for action in proposal.suggested_actions:
        lines.append(f"• {action}")
    
    return "\n".join(lines)
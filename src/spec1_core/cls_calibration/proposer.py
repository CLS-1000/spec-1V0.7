from .schemas import ThresholdSet, CalibrationProposal
from .analyzer import CalibrationAnalyzer

class ThresholdProposer:
    def __init__(self, analyzer: CalibrationAnalyzer, target_daily: int = 12):
        self.analyzer = analyzer
        self.target_daily = target_daily

    def propose(self, days: int = 30) -> CalibrationProposal:
        metrics = self.analyzer.compute_metrics(days)
        current = ThresholdSet()

        proposals = {}
        actions = []

        # Credibility tuning example
        if metrics.positive_verdict_rate < 0.4:
            proposals["credibility_min"] = max(0.45, current.credibility_min - 0.05)
            actions.append("LOWER_CREDIBILITY_BARRIER")

        # Add more rules as needed

        confidence = min(1.0, metrics.total_verdicts / 50.0)

        return CalibrationProposal(
            metrics=metrics,
            current_thresholds=current,
            proposed_thresholds=proposals,
            confidence=confidence,
            suggested_actions=actions
        )
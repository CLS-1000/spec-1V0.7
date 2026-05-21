from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class GateMetrics(BaseModel):
    gate_name: str
    pass_rate: float
    precision: float
    recall_gap: float
    failure_count: int

class CalibrationMetrics(BaseModel):
    period_days: int
    total_opportunities: int
    total_verdicts: int
    positive_verdict_rate: float
    gate_metrics: Dict[str, GateMetrics]
    current_volume: int
    target_volume: int = 15

class ThresholdSet(BaseModel):
    credibility_min: float = 0.60
    volume_min: float = 0.30
    novelty_min_hits: int = 1
    composite_standard: float = 0.55
    composite_elevated: float = 0.75
    effective_date: datetime

class CalibrationProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"cal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: CalibrationMetrics
    current_thresholds: ThresholdSet
    proposed_thresholds: Dict[str, Any]
    confidence: float
    suggested_actions: List[str]
    status: str = "pending"
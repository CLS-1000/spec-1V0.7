from .analyzer import CalibrationAnalyzer
from .proposer import ThresholdProposer
from .store import CalibrationStore
from .report import generate_report
from .schemas import CalibrationProposal

class CalibrationAdjuster:
    def __init__(self, verdict_store, opportunity_store):
        self.analyzer = CalibrationAnalyzer(verdict_store, opportunity_store)
        self.proposer = ThresholdProposer(self.analyzer)
        self.store = CalibrationStore()

    def propose(self, days: int = 30, dry_run: bool = True) -> CalibrationProposal:
        proposal = self.proposer.propose(days)
        
        if not dry_run:
            self.store.save(proposal)
        
        print(generate_report(proposal))
        return proposal

    def apply(self, proposal_id: str):
        print(f"✅ Applied proposal {proposal_id}")
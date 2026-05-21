from datetime import datetime
from typing import Optional, List
import json
from .schemas import CalibrationProposal
from spec1_core.cls_db import dual_write  # Adjust import to match your repo pattern

class CalibrationStore:
    JSONL_PATH = "data/calibration_proposals.jsonl"
    TABLE_NAME = "calibration_proposals"

    @staticmethod
    def save(proposal: CalibrationProposal):
        dual_write(
            proposal,
            jsonl_path=CalibrationStore.JSONL_PATH,
            sqlite_table=CalibrationStore.TABLE_NAME,
            timestamp_field="timestamp"
        )

    @staticmethod
    def get_latest() -> Optional[CalibrationProposal]:
        try:
            with open(CalibrationStore.JSONL_PATH, 'r') as f:
                lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1])
                    return CalibrationProposal.model_validate(last)
        except Exception:
            pass
        return None
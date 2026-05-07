"""CLI: produce a calibration report and write calibration_report.md + .jsonl.

Usage:
    python -m spec1_engine.tools.calibration_propose
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    # Ensure src/ is on the path when run directly
    src_dir = Path(__file__).parent.parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from spec1_engine.intelligence.store import JsonlStore
    from cls_verdicts.store import VerdictStore
    from cls_calibration.producer import produce_report
    from cls_calibration.formatter import format_report_markdown

    intel_path = Path(os.environ.get("SPEC1_STORE_PATH", "spec1_intelligence.jsonl"))
    verdicts_path = Path(os.environ.get("SPEC1_VERDICTS_PATH", "verdicts.jsonl"))
    out_dir = Path(os.environ.get("SPEC1_CALIBRATION_DIR", "."))

    intel_store = JsonlStore(intel_path)
    verdict_store = VerdictStore(verdicts_path)

    records = [r if isinstance(r, dict) else r.to_dict() for r in intel_store.read_all(limit=10_000)]  # type: ignore[attr-defined]
    verdicts = [v.to_dict() for v in verdict_store.read_all(limit=50_000)]

    report = produce_report(records, verdicts, include_proposals=True)

    md_path = out_dir / "calibration_report.md"
    jsonl_path = out_dir / "calibration_report.jsonl"

    md_path.write_text(format_report_markdown(report), encoding="utf-8")
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(report.to_dict()) + "\n")

    print(f"Calibration report written to {md_path} and {jsonl_path}")
    print(f"  Records: {report.record_count}, Verdicts: {report.verdict_count}, Proposals: {len(report.proposals)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fail CI if hardcoded label strings found instead of spec1_labels imports."""

import re
import sys
from pathlib import Path

HARDCODED_PATTERNS = {
    r'"(HIGH|CRITICAL|MEDIUM|LOW)"': "Use PRIORITY_*/THREAT_* from spec1_labels",
    r'"(POSITIVE|NEGATIVE|NEUTRAL|MIXED)"': "Use SENTIMENT_* from spec1_labels",
    r'"(CORROBORATED|PARTIAL|UNVERIFIED|CONFLICTED)"': "Use VERIF_* from spec1_labels",
    r'"(CLEAN|HIGH_RISK|MEDIUM_RISK|LOW_RISK)"': "Use PSYOP_* from spec1_labels",
}

# Files that legitimately define these strings (the labels module itself + schemas/tests)
ALLOWLIST = {
    "spec1_labels.py",
    "cls_verdicts/schemas.py",
    "cls_psyop/schemas.py",
    "cls_leads/schemas.py",
}


def check_file(path: Path) -> list[str]:
    if any(part in str(path) for part in ALLOWLIST):
        return []
    content = path.read_text(encoding="utf-8", errors="ignore")
    errors = []
    for pattern, msg in HARDCODED_PATTERNS.items():
        for match in re.finditer(pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            errors.append(f"{path}:{line_num}: {msg} (found {match.group()!r})")
    return errors


def main() -> int:
    src_dir = Path("src")
    all_errors: list[str] = []
    for py_file in src_dir.rglob("*.py"):
        all_errors.extend(check_file(py_file))
    if all_errors:
        for error in all_errors:
            print(error)
        return 1
    print("✓ No hardcoded label strings found")
    return 0


if __name__ == "__main__":
    sys.exit(main())

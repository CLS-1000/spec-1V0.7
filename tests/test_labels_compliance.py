"""Tests for spec1_labels compliance — no hardcoded label strings in source.

These tests import the check_hardcoded_labels script and run it against the
src/ directory, ensuring that cls_psyop, cls_leads, and related modules use
the canonical label constants from spec1_labels rather than bare strings.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the .github/scripts directory is importable for testing
SCRIPTS_DIR = Path(__file__).parent.parent / ".github" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from check_hardcoded_labels import check_file, scan  # noqa: E402


SRC_DIR = Path(__file__).parent.parent / "src"


class TestCheckHardcodedLabels:
    def test_cls_leads_generator_clean(self):
        """cls_leads/generator.py must not contain hardcoded priority strings."""
        path = SRC_DIR / "spec1_analytics" / "cls_leads" / "generator.py"
        violations = check_file(path)
        assert violations == [], (
            f"Found hardcoded labels in {path}:\n"
            + "\n".join(f"  line {ln}: {label}" for ln, label, _ in violations)
        )

    def test_cls_psyop_patterns_clean(self):
        """cls_psyop/patterns.py must not contain hardcoded threat level strings."""
        path = SRC_DIR / "spec1_analytics" / "cls_psyop" / "patterns.py"
        violations = check_file(path)
        assert violations == [], (
            f"Found hardcoded labels in {path}:\n"
            + "\n".join(f"  line {ln}: {label}" for ln, label, _ in violations)
        )

    def test_cls_psyop_scorer_clean(self):
        """cls_psyop/scorer.py must not contain hardcoded risk classification strings."""
        path = SRC_DIR / "spec1_analytics" / "cls_psyop" / "scorer.py"
        violations = check_file(path)
        assert violations == [], (
            f"Found hardcoded labels in {path}:\n"
            + "\n".join(f"  line {ln}: {label}" for ln, label, _ in violations)
        )

    def test_spec1_labels_itself_excluded(self):
        """spec1_labels.py must be excluded from the scan (it defines the labels)."""
        path = SRC_DIR / "spec1_labels.py"
        violations = check_file(path)
        # spec1_labels.py is in _EXCLUDES so check_file is called directly here;
        # the scan() function would skip it via _is_excluded() — we confirm here that
        # any violations in spec1_labels.py itself are *ignored by the scanner*
        import check_hardcoded_labels as chk
        findings = chk.scan(SRC_DIR)
        spec1_labels_violations = [p for p in findings if p.name == "spec1_labels.py"]
        assert spec1_labels_violations == []

    def test_scan_excludes_test_files(self, tmp_path: Path):
        """Test files containing label strings should not be flagged."""
        test_file = tmp_path / "test_something.py"
        test_file.write_text('priority = "CRITICAL"\nrisk = "HIGH_RISK"\n')

        import check_hardcoded_labels as chk
        findings = chk.scan(tmp_path)
        assert findings == {}

    def test_check_file_flags_hardcoded_string_in_leads(self, tmp_path: Path):
        """A synthetic file with hardcoded CRITICAL should be flagged."""
        py_file = tmp_path / "cls_leads" / "example.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text('from spec1_labels import PRIORITY_HIGH\npriority = "CRITICAL"\n')

        violations = check_file(py_file)
        assert any(label == "CRITICAL" for _, label, _ in violations)

    def test_check_file_ignores_non_label_strings(self, tmp_path: Path):
        """Non-label strings should not be flagged."""
        py_file = tmp_path / "cls_leads" / "ok.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text('from spec1_labels import PRIORITY_HIGH\nfoo = "some_other_value"\n')

        violations = check_file(py_file)
        assert violations == []

    def test_full_src_scan_passes(self):
        """The full src/ directory must be free of flagged hardcoded labels."""
        import check_hardcoded_labels as chk
        findings = chk.scan(SRC_DIR)
        if findings:
            lines = []
            for path, violations in findings.items():
                for lineno, label, reason in violations:
                    lines.append(f"  {path}:{lineno}: {reason}")
            pytest.fail("Hardcoded label violations found:\n" + "\n".join(lines))

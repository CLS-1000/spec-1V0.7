"""Markdown formatter for CalibrationReport."""

from __future__ import annotations

from cls_calibration.schemas import CalibrationReport


def format_report_markdown(report: CalibrationReport) -> str:
    """Render a CalibrationReport as a human-readable Markdown document."""
    lines: list[str] = [
        f"# Calibration Report",
        f"",
        f"**Report ID:** {report.report_id}  ",
        f"**Generated:** {report.generated_at}  ",
        f"**Intelligence records:** {report.record_count}  ",
        f"**Verdicts filed:** {report.verdict_count}  ",
        f"",
    ]

    def _table(buckets: list) -> list[str]:
        if not buckets:
            return ["_No data_", ""]
        rows = [
            "| Bucket | Records | Verdicts | TP | FP | Precision | TP-Rate |",
            "|--------|---------|----------|----|-----|-----------|---------|",
        ]
        for b in buckets:
            prec = f"{b.precision:.2f}" if b.precision >= 0 else "—"
            tpr = f"{b.tp_rate:.2f}" if b.tp_rate >= 0 else "—"
            rows.append(
                f"| {b.bucket_label} | {b.record_count} | {b.verdict_count} "
                f"| {b.tp_count} | {b.fp_count} | {prec} | {tpr} |"
            )
        return rows + [""]

    lines += ["## Confidence buckets", ""]
    lines += _table(report.confidence_buckets)

    lines += ["## Source-weight buckets", ""]
    lines += _table(report.source_weight_buckets)

    lines += ["## Analyst-weight buckets", ""]
    lines += _table(report.analyst_weight_buckets)

    if report.proposals:
        lines += ["## Adjustment proposals _(descriptive only — never auto-applied)_", ""]
        for p in report.proposals:
            lines.append(
                f"- **{p.dimension}** bucket `{p.bucket_label}`: "
                f"current {p.current_value:.2f} → suggested **{p.suggested_value:.2f}**  "
            )
            lines.append(f"  _{p.reason}_")
            lines.append("")
    else:
        lines += ["## Adjustment proposals", "", "_None — insufficient verdict data or no significant drift detected._", ""]

    return "\n".join(lines)

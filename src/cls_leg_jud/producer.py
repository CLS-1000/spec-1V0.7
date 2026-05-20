"""Producer for Legislative & Judicial Desk brief."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from cls_leg_jud.schemas import (
    LegJudBrief,
    LegJudSection,
    SECTION_KINDS,
    SECTION_TITLES,
)

# Domain routing: section kind → list of domain prefixes (or exact strings)
SECTION_DOMAINS: dict[str, list[str]] = {
    "federal_members":      ["congress.vote", "congress.hearing", "congress.sponsor"],
    "federal_lobbying":     ["fara.filing", "lda.filing"],
    "judicial":             ["judicial."],
    "state_leg":            ["state_leg."],
    "geopolitical_context": ["geo."],
}

# Words prohibited in stated_purpose_vs_beneficiary output
_PROHIBITED = {
    "corrupt", "honest", "partisan", "scheming", "admit", "deny",
    "claim", "scheme", "push", "plot", "alarmingly", "surprisingly", "conveniently",
}

_FRESHNESS_WINDOW_HOURS = 72


def _short_id(run_id: str) -> str:
    """First 8 chars of run_id."""
    return run_id[:8]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_eligible(record: dict) -> bool:
    """Return True if record passes confidence and freshness thresholds."""
    confidence = record.get("composite_confidence", 0.0)
    if confidence <= 0.40:
        return False

    # Check ongoing flag in metadata
    metadata = record.get("metadata", {}) or {}
    if metadata.get("ongoing", False):
        return True

    # Check freshness — published_at or analyzed_at within 72 hours
    for ts_field in ("published_at", "analyzed_at", "created_at"):
        ts_val = record.get(ts_field)
        if ts_val:
            try:
                if isinstance(ts_val, str):
                    # Handle ISO format with or without timezone
                    ts_val = ts_val.rstrip("Z")
                    if "+" in ts_val:
                        dt = datetime.fromisoformat(ts_val)
                    else:
                        dt = datetime.fromisoformat(ts_val).replace(tzinfo=timezone.utc)
                elif isinstance(ts_val, (int, float)):
                    dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                else:
                    continue
                if _now_utc() - dt <= timedelta(hours=_FRESHNESS_WINDOW_HOURS):
                    return True
            except (ValueError, OSError, OverflowError):
                continue

    # If no timestamp found, fall back to confidence-only check (already passed above)
    return True


def _route_to_section(domain: str) -> Optional[str]:
    """Map a domain string to a section kind using prefix matching."""
    if not domain:
        return None
    for section_kind, prefixes in SECTION_DOMAINS.items():
        for prefix in prefixes:
            if domain == prefix or domain.startswith(prefix):
                return section_kind
    return None


def _sanitise(text: str) -> str:
    """Remove prohibited words from output text (case-insensitive replacement)."""
    if not text:
        return text
    import re
    for word in _PROHIBITED:
        # Replace whole-word occurrences, case-insensitive
        text = re.sub(r"\b" + re.escape(word) + r"\b", "[REDACTED]", text, flags=re.IGNORECASE)
    return text


def _build_executive_summary(routed: dict[str, list[dict]], run_id: str) -> LegJudSection:
    """Top 5 eligible records by composite_confidence, one bullet per record."""
    all_records: list[dict] = []
    for records in routed.values():
        all_records.extend(records)

    # Sort by composite_confidence descending, take top 5
    top5 = sorted(all_records, key=lambda r: r.get("composite_confidence", 0.0), reverse=True)[:5]

    record_ids = []
    bullets = []
    sid = _short_id(run_id)

    for rec in top5:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        subject = rec.get("subject") or rec.get("title") or rec.get("headline") or "Unknown subject"
        action = rec.get("action") or rec.get("summary") or rec.get("classification") or ""
        conf = rec.get("composite_confidence", 0.0)
        bullet = f"- {subject}"
        if action:
            bullet += f" — {action[:200]}"
        bullet += f" [conf:{conf:.2f}] [run:{sid}]"
        bullets.append(_sanitise(bullet))

    body = "\n".join(bullets) if bullets else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="executive_summary",
        title=SECTION_TITLES["executive_summary"],
        body=body,
        record_ids=record_ids,
    )


def _build_federal_members(records: list[dict], run_id: str) -> LegJudSection:
    """Organise by chamber (SENATE then HOUSE), format: bill/vote, member position, run_id."""
    if not records:
        return _no_signal("federal_members")

    sid = _short_id(run_id)
    senate_lines: list[str] = []
    house_lines: list[str] = []
    other_lines: list[str] = []
    record_ids: list[str] = []

    for rec in records:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        metadata = rec.get("metadata", {}) or {}
        chamber = (metadata.get("chamber") or rec.get("chamber") or "").upper()
        bill = metadata.get("bill") or rec.get("bill") or rec.get("title") or "Unknown bill"
        vote = metadata.get("vote") or rec.get("vote") or ""
        member = metadata.get("member") or rec.get("member") or rec.get("subject") or "Unknown member"
        position = metadata.get("position") or rec.get("position") or ""
        domain = rec.get("domain", "")
        conf = rec.get("composite_confidence", 0.0)

        action_type = "Hearing" if "hearing" in domain else ("Vote" if "vote" in domain else "Sponsor")
        line_parts = [f"  - [{action_type}] {bill}"]
        if vote:
            line_parts.append(f"Vote: {vote}")
        line_parts.append(f"Member: {member}")
        if position:
            line_parts.append(f"Position: {position}")
        line_parts.append(f"conf:{conf:.2f}")
        line_parts.append(f"run:{sid}")
        line = " | ".join(line_parts[:1]) + " | " + " | ".join(line_parts[1:])

        if chamber == "SENATE":
            senate_lines.append(line)
        elif chamber == "HOUSE":
            house_lines.append(line)
        else:
            other_lines.append(line)

    sections_text: list[str] = []
    if senate_lines:
        sections_text.append("**SENATE**")
        sections_text.extend(senate_lines)
    if house_lines:
        sections_text.append("**HOUSE**")
        sections_text.extend(house_lines)
    if other_lines:
        sections_text.append("**OTHER**")
        sections_text.extend(other_lines)

    body = _sanitise("\n".join(sections_text)) if sections_text else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="federal_members",
        title=SECTION_TITLES["federal_members"],
        body=body,
        record_ids=record_ids,
    )


def _build_federal_lobbying(records: list[dict], run_id: str) -> LegJudSection:
    """Registrant, foreign_principal or client, contact targets, filing date, run_id."""
    if not records:
        return _no_signal("federal_lobbying")

    sid = _short_id(run_id)
    lines: list[str] = []
    record_ids: list[str] = []

    for rec in records:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        metadata = rec.get("metadata", {}) or {}
        registrant = metadata.get("registrant") or rec.get("registrant") or rec.get("subject") or "Unknown registrant"
        foreign_principal = metadata.get("foreign_principal") or rec.get("foreign_principal") or ""
        client = metadata.get("client") or rec.get("client") or ""
        contact_targets = metadata.get("contact_targets") or rec.get("contact_targets") or []
        filing_date = metadata.get("filing_date") or rec.get("filing_date") or rec.get("published_at", "")[:10]
        conf = rec.get("composite_confidence", 0.0)

        principal_str = foreign_principal if foreign_principal else (client if client else "Not disclosed")
        targets_str = ", ".join(contact_targets) if isinstance(contact_targets, list) else str(contact_targets)

        line = (
            f"  - Registrant: {registrant} | Principal/Client: {principal_str}"
        )
        if targets_str:
            line += f" | Targets: {targets_str}"
        line += f" | Filed: {filing_date} | conf:{conf:.2f} | run:{sid}"
        lines.append(line)

    body = _sanitise("\n".join(lines)) if lines else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="federal_lobbying",
        title=SECTION_TITLES["federal_lobbying"],
        body=body,
        record_ids=record_ids,
    )


def _build_judicial(records: list[dict], run_id: str) -> LegJudSection:
    """Judge, action type, case_ref, prior ties, run_id."""
    if not records:
        return _no_signal("judicial")

    sid = _short_id(run_id)
    lines: list[str] = []
    record_ids: list[str] = []

    for rec in records:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        metadata = rec.get("metadata", {}) or {}
        judge = metadata.get("judge") or rec.get("judge") or rec.get("subject") or "Unknown judge"
        action_type = metadata.get("action_type") or rec.get("action_type") or rec.get("classification") or "Unknown action"
        case_ref = metadata.get("case_ref") or rec.get("case_ref") or ""
        prior_ties = metadata.get("prior_ties") or rec.get("prior_ties") or []
        conf = rec.get("composite_confidence", 0.0)

        ties_str = ", ".join(prior_ties) if isinstance(prior_ties, list) else str(prior_ties)

        line = f"  - Judge: {judge} | Action: {action_type}"
        if case_ref:
            line += f" | Case: {case_ref}"
        if ties_str:
            line += f" | Prior ties: {ties_str}"
        line += f" | conf:{conf:.2f} | run:{sid}"
        lines.append(line)

    body = _sanitise("\n".join(lines)) if lines else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="judicial",
        title=SECTION_TITLES["judicial"],
        body=body,
        record_ids=record_ids,
    )


def _build_state_leg(records: list[dict], run_id: str) -> LegJudSection:
    """State, bill, sponsor, status, disclosure_regime; DISCLOSURE GAP if missing."""
    if not records:
        return _no_signal("state_leg")

    sid = _short_id(run_id)
    lines: list[str] = []
    record_ids: list[str] = []

    for rec in records:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        metadata = rec.get("metadata", {}) or {}
        state = metadata.get("state") or rec.get("state") or "Unknown state"
        bill = metadata.get("bill") or rec.get("bill") or rec.get("title") or "Unknown bill"
        sponsor = metadata.get("sponsor") or rec.get("sponsor") or rec.get("subject") or "Unknown sponsor"
        status = metadata.get("status") or rec.get("status") or ""
        disclosure_regime = metadata.get("disclosure_regime") or rec.get("disclosure_regime") or ""
        disclosure_gap = metadata.get("disclosure_gap", False) or rec.get("disclosure_gap", False)
        conf = rec.get("composite_confidence", 0.0)

        if disclosure_gap:
            lines.append(f"  DISCLOSURE GAP: {state}")

        line = f"  - {state} | Bill: {bill} | Sponsor: {sponsor}"
        if status:
            line += f" | Status: {status}"
        if disclosure_regime:
            line += f" | Disclosure: {disclosure_regime}"
        line += f" | conf:{conf:.2f} | run:{sid}"
        lines.append(line)

    body = _sanitise("\n".join(lines)) if lines else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="state_leg",
        title=SECTION_TITLES["state_leg"],
        body=body,
        record_ids=record_ids,
    )


def _build_stated_purpose_vs_beneficiary(all_eligible: list[dict], run_id: str) -> LegJudSection:
    """High-confidence records (> 0.60): stated_purpose, observed_beneficiary, delta."""
    sid = _short_id(run_id)
    high_conf = [r for r in all_eligible if r.get("composite_confidence", 0.0) > 0.60]

    if not high_conf:
        return _no_signal("stated_purpose_vs_beneficiary")

    record_ids: list[str] = []
    blocks: list[str] = []

    for rec in high_conf:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        metadata = rec.get("metadata", {}) or {}

        # stated_purpose
        stated_purpose = rec.get("summary") or rec.get("bill_text") or metadata.get("stated_purpose") or "Not stated on record."

        # observed_beneficiary — build from metadata fields
        beneficiary_parts: list[str] = []
        sector_tags = metadata.get("sector_tags") or []
        if sector_tags:
            if isinstance(sector_tags, list):
                beneficiary_parts.append(", ".join(sector_tags))
            else:
                beneficiary_parts.append(str(sector_tags))

        fara_matches = metadata.get("fara_matches") or []
        if fara_matches:
            if isinstance(fara_matches, list):
                fara_str = ", ".join(fara_matches)
            else:
                fara_str = str(fara_matches)
            beneficiary_parts.append(f"FARA registrant overlap: {fara_str}")

        committee_overlap = metadata.get("committee_overlap") or []
        if committee_overlap:
            if isinstance(committee_overlap, list):
                committee_str = ", ".join(committee_overlap)
            else:
                committee_str = str(committee_overlap)
            beneficiary_parts.append(f"Committee assignment overlap: {committee_str}")

        observed_beneficiary = "; ".join(beneficiary_parts) if beneficiary_parts else "Not identified in available metadata."

        # delta — neutral divergence description
        sector_for_delta = sector_tags[0] if isinstance(sector_tags, list) and sector_tags else (str(sector_tags) if sector_tags else "stated")
        if observed_beneficiary != "Not identified in available metadata.":
            delta = f"Record summary deviates from {sector_for_delta} baseline in that {observed_beneficiary}."
        else:
            delta = "Insufficient metadata to determine divergence from stated purpose."

        subject = rec.get("subject") or rec.get("title") or rec.get("headline") or "Record"
        conf = rec.get("composite_confidence", 0.0)

        block_lines = [
            f"**{subject}** [conf:{conf:.2f}] [run:{sid}]",
            f"  Stated Purpose: {stated_purpose[:300]}",
            f"  Observed Beneficiary: {observed_beneficiary[:300]}",
            f"  Delta: {delta[:400]}",
        ]
        blocks.append(_sanitise("\n".join(block_lines)))

    body = "\n\n".join(blocks) if blocks else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="stated_purpose_vs_beneficiary",
        title=SECTION_TITLES["stated_purpose_vs_beneficiary"],
        body=body,
        record_ids=record_ids,
    )


def _build_geopolitical_context(records: list[dict], run_id: str) -> LegJudSection:
    """Geopolitical context section from geo.-domain records."""
    if not records:
        return _no_signal("geopolitical_context")

    sid = _short_id(run_id)
    lines: list[str] = []
    record_ids: list[str] = []

    for rec in records:
        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)
        metadata = rec.get("metadata", {}) or {}
        country = metadata.get("country") or rec.get("country") or ""
        region = metadata.get("region") or rec.get("region") or ""
        subject = rec.get("subject") or rec.get("title") or rec.get("headline") or "Unknown"
        summary = rec.get("summary") or ""
        conf = rec.get("composite_confidence", 0.0)
        geo_label = country or region or "Unknown region"

        line = f"  - [{geo_label}] {subject}"
        if summary:
            line += f" — {summary[:200]}"
        line += f" | conf:{conf:.2f} | run:{sid}"
        lines.append(line)

    body = _sanitise("\n".join(lines)) if lines else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="geopolitical_context",
        title=SECTION_TITLES["geopolitical_context"],
        body=body,
        record_ids=record_ids,
    )


def _build_story_leads(all_eligible: list[dict], run_id: str) -> LegJudSection:
    """Surface analyst_leads from records — do NOT regenerate."""
    sid = _short_id(run_id)
    blocks: list[str] = []
    record_ids: list[str] = []

    for rec in all_eligible:
        metadata = rec.get("metadata", {}) or {}
        analyst_leads = metadata.get("analyst_leads") or []
        if not analyst_leads:
            continue

        rid = rec.get("record_id") or rec.get("id", "")
        if rid:
            record_ids.append(rid)

        freshness_window = rec.get("freshness_window", "72h")
        conf = rec.get("composite_confidence", 0.0)

        for lead in analyst_leads:
            if not isinstance(lead, dict):
                continue
            question = lead.get("question", "Not specified")
            contacts = lead.get("contacts", "Not specified")
            documents = lead.get("documents", "Not specified")
            block = (
                f"**The Question** — {question}\n"
                f"**Who to Call** — {contacts}\n"
                f"**Documents to Request** — {documents}\n"
                f"**Window & Confidence** — {freshness_window} / {conf:.2f}\n"
                f"run_id: {sid}"
            )
            blocks.append(_sanitise(block))

    body = "\n\n".join(blocks) if blocks else "NO SIGNAL THIS CYCLE"
    return LegJudSection(
        kind="story_leads",
        title=SECTION_TITLES["story_leads"],
        body=body,
        record_ids=record_ids,
    )


def _no_signal(kind: str) -> LegJudSection:
    """Return a section with body 'NO SIGNAL THIS CYCLE'."""
    return LegJudSection(
        kind=kind,
        title=SECTION_TITLES[kind],
        body="NO SIGNAL THIS CYCLE",
        record_ids=[],
    )


def produce_brief(
    records: list[dict],
    run_id: str = "",
    date: Optional[str] = None,
) -> LegJudBrief:
    """Synthesise a LegJudBrief from a list of IntelligenceRecord dicts."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_records = len(records)

    # Filter eligible records
    eligible: list[dict] = [r for r in records if _is_eligible(r)]
    eligible_count = len(eligible)

    # Route eligible records to sections
    routed: dict[str, list[dict]] = {kind: [] for kind in SECTION_KINDS}
    for rec in eligible:
        domain = rec.get("domain", "")
        section_kind = _route_to_section(domain)
        if section_kind is not None:
            routed[section_kind].append(rec)
        # Records with no domain match still feed executive_summary, stated_purpose, story_leads

    # Build sections
    sections: list[LegJudSection] = []

    if eligible_count == 0:
        # Full termination: all sections get NO SIGNAL
        for kind in SECTION_KINDS:
            sections.append(_no_signal(kind))
    else:
        # executive_summary uses all eligible records
        sections.append(_build_executive_summary(routed, run_id))
        sections.append(_build_federal_members(routed["federal_members"], run_id))
        sections.append(_build_federal_lobbying(routed["federal_lobbying"], run_id))
        sections.append(_build_judicial(routed["judicial"], run_id))
        sections.append(_build_state_leg(routed["state_leg"], run_id))
        # stated_purpose_vs_beneficiary works on ALL eligible records
        sections.append(_build_stated_purpose_vs_beneficiary(eligible, run_id))
        sections.append(_build_geopolitical_context(routed["geopolitical_context"], run_id))
        # story_leads works on ALL eligible records
        sections.append(_build_story_leads(eligible, run_id))

    brief = LegJudBrief(
        brief_id=LegJudBrief.make_id(run_id),
        run_id=run_id,
        date=date,
        sections=sections,
        total_records=total_records,
        eligible_records=eligible_count,
    )
    return brief

"""Daily intelligence brief generator.

Calls Claude Sonnet to write a publishable brief from today's scored records.
Falls back to a raw-stats brief on any API error — never crashes the cycle.
"""

import os
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

import logging
from datetime import datetime, timezone

import anthropic

from spec1_labels import VERIF_CORROBORATED
from spec1_core.briefing.templates import (
    GEO_SYSTEM_PROMPT,
    GEO_USER_PROMPT_TEMPLATE,
    LEG_SYSTEM_PROMPT,
    LEG_USER_PROMPT_TEMPLATE,
)
from spec1_core.briefing.brief_package_templates import BRIEF_SYSTEM, BRIEF_USER

try:
    from zoneinfo import ZoneInfo
    _PT_ZONE: object = ZoneInfo("America/Los_Angeles")
except Exception:
    from datetime import timedelta
    _PT_ZONE = timezone(timedelta(hours=-7))

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4000

# Sources that map to Cyber / Info Ops domain
_CYBER_SOURCES = {
    "cipher_brief", "just_security", "lawfare",
    "cyberscoop", "recordedfuture", "krebs",
}

# Sources that map to Geopolitics domain
_GEO_SOURCES = {
    "war_on_the_rocks", "rand", "atlantic_council",
    "defense_one", "foreign_affairs", "bellingcat",
}


def _classify_domain(record: dict) -> str:
    """Return 'cyber' or 'geo' based on signal source."""
    src = str(record.get("signal_source", "")).lower()
    if src in _CYBER_SOURCES:
        return "cyber"
    return "geo"


def _format_record(record: dict) -> str:
    """Format a single record for the prompt — readable, not raw JSON."""
    source = record.get("signal_source", record.get("source", "unknown"))
    pattern = record.get("pattern", "—")
    confidence = record.get("confidence", record.get("outcome_confidence", 0.0))
    classification = record.get("outcome_classification", record.get("classification", "—"))
    priority = record.get("opportunity_priority", "—")
    url = record.get("signal_url", "")
    url_str = f" | {url}" if url else ""
    return (
        f"{source.upper()} | {pattern} | "
        f"confidence={float(confidence):.2f} | classification={classification} | "
        f"priority={priority}{url_str}"
    )


def _build_prompt(records: list[dict], cycle_stats: dict, mode: str = "standard") -> str:
    """Build the filled prompt template string for the given mode."""
    elevated = [
        r for r in records
        if r.get("outcome_classification", r.get("classification", "")) in (VERIF_CORROBORATED, "ESCALATE")
    ]
    remaining = [r for r in records if r not in elevated]
    standard_top10 = sorted(
        remaining,
        key=lambda r: float(r.get("confidence", r.get("outcome_confidence", 0.0))),
        reverse=True,
    )[:10]

    geo_count = sum(1 for r in records if _classify_domain(r) == "geo")
    cyber_count = sum(1 for r in records if _classify_domain(r) == "cyber")

    elevated_block = (
        "\n".join(_format_record(r) for r in elevated)
        if elevated else "(none)"
    )
    standard_block = (
        "\n".join(_format_record(r) for r in standard_top10)
        if standard_top10 else "(none)"
    )

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pt_now = datetime.now(_PT_ZONE)
    date_long = pt_now.strftime("%A, %d %B %Y")
    time_pt = pt_now.strftime("%H:%M")
    _doms = []
    if geo_count > 0:
        _doms.append("Geopolitics")
    if cyber_count > 0:
        _doms.append("Cyber · Info Ops")
    active_domains = " · ".join(_doms) if _doms else "—"
    issue_number = cycle_stats.get("issue_number", "—")

    # Format evidence chains for the template
    raw_chains: list[dict] = cycle_stats.get("psyop_evidence_chains", [])
    if raw_chains:
        chain_blocks = []
        for ec in raw_chains:
            sources_str = ", ".join(
                m.get("source", "") for m in ec.get("source_metadata", [])
            ) or "—"
            excerpts = ec.get("raw_excerpts", [])
            excerpts_str = " | ".join(
                f"[{x.get('source', '')}] {x.get('text_snippet', '')[:200]}"
                for x in excerpts[:3]
            ) or "—"
            xrefs = ec.get("cross_references", [])
            xrefs_str = ", ".join(xrefs[:5]) or "none"
            block = (
                f"  Pattern: {ec.get('pattern_name', '—')} | "
                f"Confidence: {ec.get('confidence', 0.0):.2f}\n"
                f"  Summary: {ec.get('summary', '—')}\n"
                f"  Sources: {sources_str}\n"
                f"  Excerpts: {excerpts_str}\n"
                f"  Cross-references: {xrefs_str}"
            )
            chain_blocks.append(block)
        evidence_chains_str = "\n\n".join(chain_blocks)
    else:
        evidence_chains_str = "(none)"

    if mode == "geopolitics":
        tmpl = GEO_USER_PROMPT_TEMPLATE
    elif mode == "legislative":
        tmpl = LEG_USER_PROMPT_TEMPLATE
    else:
        tmpl = BRIEF_USER

    return tmpl.format(
        run_id=cycle_stats.get("run_id", "—"),
        timestamp=cycle_stats.get("finished_at", cycle_stats.get("timestamp", "—")),
        signal_count=cycle_stats.get("signals_harvested", cycle_stats.get("signal_count", 0)),
        opportunity_count=cycle_stats.get("opportunities_found", 0),
        record_count=cycle_stats.get("records_stored", cycle_stats.get("record_count", len(records))),
        elevated_count=len(elevated),
        elevated_records=elevated_block,
        standard_records=standard_block,
        geo_count=geo_count,
        cyber_count=cyber_count,
        date=date_str,
        date_long=date_long,
        time_pt=time_pt,
        active_domains=active_domains,
        issue_number=issue_number,
        psyop_classification=cycle_stats.get("psyop_classification", "—"),
        psyop_score=cycle_stats.get("psyop_score", "—"),
        psyop_patterns_fired=cycle_stats.get("psyop_patterns_fired", []),
        evidence_count=len(raw_chains),
        evidence_chains=evidence_chains_str,
    )


def _fallback_brief(cycle_stats: dict) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = cycle_stats.get("run_id", "—")
    harvested = cycle_stats.get("signals_harvested", 0)
    opportunities = cycle_stats.get("opportunities_found", 0)
    stored = cycle_stats.get("records_stored", 0)
    errors = cycle_stats.get("errors", [])
    finished = cycle_stats.get("finished_at", "—")

    error_block = ""
    if errors:
        error_lines = "\n".join(f"  - {e}" for e in errors)
        error_block = f"\n\n**Harvest errors ({len(errors)}):**\n{error_lines}"

    return (
        f"## SPEC-1 DAILY BRIEF — {date_str}\n\n"
        f"*AI brief unavailable — API key not configured. Cycle stats below.*\n\n"
        f"**Run:** {run_id}  \n"
        f"**Completed:** {finished}  \n"
        f"**Signals harvested:** {harvested}  \n"
        f"**Opportunities found:** {opportunities}  \n"
        f"**Records stored:** {stored}"
        f"{error_block}"
    )


def generate_brief(records: list[dict], cycle_stats: dict, mode: str = "standard") -> tuple[str, str]:
    """Generate the daily intelligence brief via Claude.

    Returns a (brief, prompts_text) tuple where *brief* is the generated
    markdown and *prompts_text* is the full prompts payload (system + user)
    that was sent to the model.  On any failure the brief is a fallback
    string; prompts_text is still populated when available.
    Never raises.

    mode: "standard" (default SPEC-1 brief), "geopolitics" (Geopolitics & Policy Desk),
          or "legislative" (Legislative & Judicial Desk).
          Legislative mode is triggered by cls_legislative when that module
          feeds into the brief pipeline. Not yet auto-triggered by cycle.py.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip().lstrip('\ufeff')
    if not api_key:
        print("[briefing] ANTHROPIC_API_KEY not set in environment — returning fallback brief")
        logger.warning("ANTHROPIC_API_KEY not set — returning fallback brief")
        return _fallback_brief(cycle_stats), ""

    if mode == "geopolitics":
        sys_prompt = GEO_SYSTEM_PROMPT
    elif mode == "legislative":
        sys_prompt = LEG_SYSTEM_PROMPT
    else:
        sys_prompt = BRIEF_SYSTEM

    prompts_text = ""
    try:
        user_prompt = _build_prompt(records, cycle_stats, mode=mode)
        prompts_text = f"## SYSTEM PROMPT\n\n{sys_prompt.strip()}\n\n---\n\n## USER PROMPT\n\n{user_prompt.strip()}\n"
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        brief = message.content[0].text.strip()
        logger.info("Brief generated (mode=%s) — %d words", mode, len(brief.split()))
        return brief, prompts_text
    except Exception as exc:
        print(f"[briefing] API call failed: {type(exc).__name__}: {exc}")
        logger.error("Brief generation failed: %s", exc)
        return _fallback_brief(cycle_stats), prompts_text

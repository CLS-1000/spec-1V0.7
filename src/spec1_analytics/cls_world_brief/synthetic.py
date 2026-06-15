# @domain:   spec-1
# @module:   cls_world_brief_synthetic
# @loc:      _SCRATCH
# @status:   drafting
# @depends:  NONE

"""Synthetic brief generator for demonstration and testing.

Generates realistic SPEC-1 intelligence briefs with plausible geopolitical
signal patterns. Used for landing page showcase and development fixtures.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from spec1_analytics.cls_world_brief.schemas import BriefSection, WorldBrief


# Realistic signal clusters by date offset
_SYNTHETIC_BRIEFS = {
    0: {
        "headline": "Taiwan semiconductor exports show pressure. US defense spending signals diverging.",
        "summary": (
            "SPEC-1 cycle on 2026-06-02 processed 847 signals. "
            "No elevated geopolitical signals crossed confidence threshold today. "
            "Baseline activity across defense contracting, energy markets, and congressional trade intelligence. "
            "Chip export controls remain elevated; no policy shift detected. "
            "Analyst verdicts stable — calibration drift within expected bounds."
        ),
        "sections": [
            {
                "title": "Defense & Military",
                "body": (
                    "No elevated signals. Standard RSS traffic from War on the Rocks and Atlantic Council. "
                    "Articles focus on Ukraine aid pipelines and NATO standing forces. "
                    "No U.S. procurement announcements or contract awards above baseline noise threshold."
                ),
                "topics": ["defense", "nato", "ukraine"],
            },
            {
                "title": "Intelligence & Cyber",
                "body": (
                    "Cipher Brief and Just Security report routine cyber policy updates. "
                    "No attributions to nation-state actors. "
                    "Industry-led working groups on critical infrastructure remain on schedule."
                ),
                "topics": ["cyber", "intelligence", "infrastructure"],
            },
            {
                "title": "Semiconductor & Economic Statecraft",
                "body": (
                    "Taiwan trade watch active. TSMC export guidance stable. "
                    "Congressional scrutiny on advanced chip licensing remains moderate. "
                    "No new export control amendments detected in legislative pipeline."
                ),
                "topics": ["semiconductors", "trade", "congress"],
            },
            {
                "title": "Foreign Agent Activity (FARA)",
                "body": (
                    "11 new FARA registrations processed. Majority: consulting and advocacy firms. "
                    "Three registrations marked renewable energy/climate (no conflict flagged). "
                    "Defense-sector filings: zero this cycle."
                ),
                "topics": ["fara", "foreign agents", "lobbying"],
            },
        ],
        "confidence": 0.65,
    },
    -1: {
        "headline": "Russian military logistics under strain. Congressional cyber committee advances funding bill.",
        "summary": (
            "SPEC-1 cycle on 2026-06-01 processed 923 signals. "
            "Two signals exceeded elevated confidence threshold. "
            "Ukraine logistics support and U.S. cyber appropriations bill show momentum. "
            "Elevated activity in defense contracting leads and narrative anomalies detected but within expected variance."
        ),
        "sections": [
            {
                "title": "Military & Defense",
                "body": (
                    "War on the Rocks + Atlantic Council: Russian force readiness articles highlight logistics gaps. "
                    "18 Month ROI signal sourced from Cipher Brief and defense industry reports. "
                    "Confidence: 0.72. NATO expansion rhetoric remains stable across all feeds."
                ),
                "topics": ["defense", "military", "russia", "ukraine"],
            },
            {
                "title": "Cyber & Infrastructure",
                "body": (
                    "House Armed Services Cyber Subcommittee advances FY2027 appropriations (+$15M cyber personnel). "
                    "Signal sourced from Capitol Trades equity filings + congressional activity mining. "
                    "Likely beneficiaries: Northrop Grumman, Raytheon (flagged in leads)."
                ),
                "topics": ["cyber", "congress", "appropriations"],
            },
            {
                "title": "Geopolitical Tensions",
                "body": (
                    "RAND Corporation publishes assessment on Taiwan contingency costs. "
                    "Sourced by narrative analyzer; signals elevated US policy attention to IndoPacific. "
                    "No anomalies detected — signal aligns with published defense strategy documents."
                ),
                "topics": ["geopolitics", "taiwan", "china"],
            },
            {
                "title": "Intelligence Operations",
                "body": (
                    "TF-IDF narrative clustering detects slight uptick in Russia-related influence narratives "
                    "on defense/energy sector blogs. Confidence: 0.58 (just below threshold). Marked for monitoring."
                ),
                "topics": ["narrative", "influence", "monitoring"],
            },
        ],
        "confidence": 0.71,
    },
    -2: {
        "headline": "Energy markets spike on supply disruption rumors. Defense contractors announce major restructuring.",
        "summary": (
            "SPEC-1 cycle on 2026-05-31 processed 1,089 signals. "
            "Four elevated signals: energy supply anomaly, defense sector M&A, congressional hearing testimony, and two narrative clusters. "
            "Analyst leads generated. Verdicts filed: strong correlation between energy price spikes and geopolitical tension rhetoric."
        ),
        "sections": [
            {
                "title": "Energy & Economic Statecraft",
                "body": (
                    "Energy supply disruption signals from multiple RSS feeds (Defense One, Atlantic Council energy track). "
                    "Confidence: 0.76. Signals correlate with Congressional Energy Committee markup of new sanctions authorities. "
                    "Three defense contractors simultaneously announce cost-reduction restructuring. "
                    "Lead generated: investigate if restructuring driven by policy uncertainty or market conditions."
                ),
                "topics": ["energy", "economics", "sanctions"],
            },
            {
                "title": "Defense Contracting",
                "body": (
                    "Northrop Grumman, Raytheon, and Lockheed announce 2-4K layoffs targeting overhead. "
                    "FARA filings show parallel increase in lobbying engagement (3 new defense-sector registrations). "
                    "Confidence: 0.68. Narrative: restructuring as cost optimization vs. preemptive capacity reduction."
                ),
                "topics": ["defense", "contracting", "employment"],
            },
            {
                "title": "Congressional Activity",
                "body": (
                    "Senate Armed Services Committee hearing on defense industrial base resilience. "
                    "Testimony excerpts signal concern over contractor consolidation and supply chain concentration. "
                    "Signal confidence: 0.79 (sourced from House eFD and Capitol Trades equity filings)."
                ),
                "topics": ["congress", "hearing", "industry base"],
            },
            {
                "title": "Influence Operations & Narratives",
                "body": (
                    "Narrative analyzer flags coordinated messaging on 4 defense/energy blogs (same themes, 16-hour temporal cluster). "
                    "TF-IDF cosine similarity 0.82 (anomalous). Pattern: energy security + NATO expansion + defense spending justification. "
                    "Confidence: 0.61. Marked for deeper investigation — source attribution pending."
                ),
                "topics": ["narrative", "influence", "anomaly"],
            },
        ],
        "confidence": 0.73,
    },
}


def generate_synthetic_brief(
    date_offset: int = 0,
    run_id_prefix: str = "synth",
) -> WorldBrief:
    """Generate a synthetic brief for demonstration.

    Args:
        date_offset: Days in the past (0 = today, -1 = yesterday, etc.)
        run_id_prefix: Prefix for brief_id generation

    Returns:
        WorldBrief object with realistic geopolitical content.

    Raises:
        ValueError: if date_offset not in _SYNTHETIC_BRIEFS.
    """
    if date_offset not in _SYNTHETIC_BRIEFS:
        raise ValueError(
            f"date_offset {date_offset} not in available synthetics. "
            f"Available: {list(_SYNTHETIC_BRIEFS.keys())}"
        )

    now_utc = datetime.now(timezone.utc)
    brief_date = now_utc - timedelta(days=abs(date_offset))
    brief_date_str = brief_date.strftime("%Y-%m-%d")

    template = _SYNTHETIC_BRIEFS[date_offset]
    brief_id = f"{run_id_prefix}-{brief_date_str}"

    sections = [
        BriefSection(
            title=s["title"],
            body=s["body"],
            source_record_ids=[],
        )
        for s in template["sections"]
    ]

    sources = [
        "https://warontherocks.com",
        "https://www.thecipherbrief.com",
        "https://www.justsecurity.org",
        "https://www.rand.org",
        "https://www.atlanticcouncil.org",
        "https://www.defenseone.com",
    ]

    return WorldBrief(
        brief_id=brief_id,
        date=brief_date_str,
        headline=template["headline"],
        summary=template["summary"],
        sections=sections,
        sources=sources,
        confidence=template["confidence"],
        produced_at=now_utc,
        metadata={
            "synthetic": True,
            "cycle_id": f"synth-cycle-{brief_date_str}",
            "signal_count": 847 + (date_offset * 121),
            "elevated_count": abs(date_offset),
        },
    )


def generate_synthetic_briefs(count: int = 3) -> list[WorldBrief]:
    """Generate multiple synthetic briefs spanning the last N days.

    Args:
        count: Number of briefs to generate (max 3, corresponding to offsets 0, -1, -2)

    Returns:
        List of WorldBrief objects, newest first.
    """
    if count > len(_SYNTHETIC_BRIEFS):
        count = len(_SYNTHETIC_BRIEFS)

    briefs = []
    for i in range(count):
        offset = -i
        briefs.append(generate_synthetic_brief(date_offset=offset))

    return briefs

# SPEC-1: Marketable Action Plan & Go-to-Market Strategy

**"The Transparent, Deterministic OSINT Platform for Local Accountability"**

**Prepared for:** EVASTARARCANA LLC (Operator: Ominous)  
**Date:** June 2026  
**Branch:** grok/award-winning-modular-vision (full tool-audited execution)

---

## Executive Summary (The Core Thesis)

SPEC-1 has already built one of the most technically differentiated OSINT systems in the long-tail space:

- **Deterministic 4-gate validation** (Credibility, Volume, Velocity, Novelty) — fully auditable, no black-box ML.
- **Modular product architecture** (`cls_pdx1`, `cls_psyop`, `cls_fara`, `cls_journalist`, etc.) proven by rapid development of a full bi-state Portland Metro intelligence desk (293 tests, 52 files in cls_pdx1 alone).
- **Human sovereignty layer** (cls_verdicts + cls_calibration) that creates a trust and accuracy flywheel.
- **Existing daily product**: Metro Citizens Brief (MCB) — automated PDF + idempotent X publishing at 06:00 PT.
- **Sacred geometry aesthetic** (black/white, IBM Plex Mono, Metatron's Cube motifs) as a brand moat.

**The market opportunity** is massive. The global OSINT market is $8–21B+ today and growing at 15–26% CAGR. Journalism and local accountability are explicitly recognized segments, yet most commercial tools are expensive, opaque enterprise platforms (Palantir, Recorded Future) aimed at governments and large corporations.

**The gap**: Investigative journalists, small businesses, civil liberties groups, and independent researchers in specific regions have almost no affordable, transparent, high-signal automated intelligence tools.

**Bellingcat benchmark** (the closest successful analog): ~50%+ foundation/grant funding + earned revenue from training/workshops while maintaining fierce independence. They raised significantly in recent years through diversified philanthropy.

**Recommended positioning**: SPEC-1 becomes **the Bellingcat of local/regional accountability infrastructure** — starting with a deep beachhead in the Portland metro (already built) and using the modular architecture to replicate the model elsewhere.

**Near-term revenue mix (first 18 months)**:
- 60–70% Foundation & grant funding (transparency, civic tech, journalism infrastructure)
- 20–30% Paid MCB subscriptions + archives (institutional + power users)
- 10% Training, workshops, and custom adapters

This plan is grounded in direct codebase analysis, market data, local funding ecosystem research, and competitive benchmarking.

---

## Current System Strengths (What Already Exists)

From direct inspection of the repo and outputs:

- Full signal → Opportunity → Investigation → Outcome → Intelligence pipeline with 4-gate deterministic scoring.
- Multiple specialized modules already shipping real value (cls_pdx1 is the standout with deep local data models).
- Production publication system (wsb_publication.py + x.py single-writer daily at 06:00 PT).
- 1,359+ tests, strong governance (frozen core + explicit write surfaces).
- Dual-write persistence (JSONL as source of truth).
- MCP server with 12 tools.
- High-craft aesthetic already defined.

**Current weakness**: Extremely low public visibility and distribution. The technical product is ahead of the go-to-market execution.

---

## Market & Competitive Context

### OSINT Market
- Valued $8–21B+ in 2025–2026, projected $30–76B by 2034–35 (CAGRs 15–26%).
- Journalism/media and "private specialized business" are growing segments.
- Most revenue captured by large enterprise vendors. The long tail is wide open.

### Relevant Benchmark: Bellingcat
- Hybrid model: Major foundation support (Adessium, NED, etc.) + earned income from workshops, keynotes, and donations.
- Maintains strong editorial independence.
- Proves there is philanthropic appetite for high-quality, transparent OSINT that serves journalists and the public.

### Local Portland Opportunity
- Oregon Journalism Project is actively building a statewide investigative newsroom and has raised from local family foundations (Jubitz, etc.) and national players.
- American Journalism Project and similar funders are pouring money into local nonprofit news infrastructure.
- No dominant player owns automated, high-signal political/entity intelligence for the bi-state metro.

**Conclusion**: Timing is excellent for a transparent, modular, local-first tool.

---

## Positioning & Defensible Moat

**Recommended Tagline**:
> "Deterministic, auditable OSINT infrastructure for the people who actually need to know what's happening in their region."

### Core Moats (in order of strength)

1. **Architectural Moat** (strongest)
   - The `cls_*` product package model allows new intelligence domains to be added as independent products without breaking existing ones.
   - Frozen core + explicit governance makes the system unusually maintainable and extensible.

2. **Determinism + Auditability Moat**
   - Every signal is scored through explicit, versioned gates. Human calibration is logged and visible.
   - This directly addresses skepticism toward AI tools in journalism and advocacy.

3. **Local Data Moat**
   - Deep, maintained coverage of Oregon/Washington legislative, campaign finance, and entity relationships (cls_pdx1 + cls_fara + cls_congressional).

4. **Aesthetic & Craft Moat**
   - Sacred geometry + IBM Plex Mono creates instant brand recognition and premium feel.

---

## Target Audiences (Prioritized)

1. **Investigative journalists & small newsrooms** (beachhead)
   - Pain: Too many feeds, not enough time to triage.
   - Entry: Free daily MCB + paid deep archives/alerts.

2. **Civil liberties & good-government groups**
   - Pain: Need to track specific officials, donors, and conflicts quickly.
   - Entry: Custom alerts + API.

3. **Small businesses & consultants** (regulatory/political risk)
   - High willingness to pay for early warning on local policy and players.

4. **Independent researchers & grad students**
   - Lower willingness to pay but excellent for credibility and data contributions.

---

## Monetization & Revenue Paths

### Tiered Model (Recommended)

**Free Tier**
- Daily public MCB (X + basic web/email)
- Limited historical access
- Goal: Build audience and proof

**Paid Tiers**
- **Individual Pro** ($29–49/mo or $250–400/year): Full archives, alerts, API light usage.
- **Institutional / Newsroom** ($2k–8k/year): Team access, custom feeds, white-label options, priority support.
- **Enterprise / Custom** (higher): Dedicated adapters, private instances, training included.

**Earned Income Streams**
- Workshops & training (Bellingcat model): "How to build and trust deterministic OSINT systems" + hands-on with SPEC-1.
- Methodology licensing or "Accountability Desk in a Box" for other regions.
- Sponsored deep-dive reports (ethically structured).

**Philanthropic Revenue (Critical for Early Stage)**
- Target: Transparency/accountability foundations, civic tech funders, journalism infrastructure funders.
- Pitch: "We're building the reusable infrastructure layer that makes local accountability journalism 3–5x more efficient."

---

## Distribution Strategy

**Current Assets**
- Daily X publishing (06:00 PT) — habit-forming.
- High-quality PDF briefs.
- GitHub + docs site.
- MCP integration (power users via Claude).

**Priority Actions**
1. **Email is king** — Launch dedicated Metro Citizens Brief newsletter immediately (owned audience).
2. **Local media partnerships** — Formal relationships with Oregon Journalism Project, Willamette Week, Portland Mercury, Salem Reporter, etc. Offer free access in exchange for co-promotion and attribution.
3. **Amplify on X** with threads that drive to the full brief + newsletter signup.
4. **GitHub as developer funnel** — Position the modular adapters and data models as public goods.
5. **Direct founder outreach** to the funders and organizations already active in the Oregon Journalism Project ecosystem.

---

## Phased 18-Month Action Plan

**Phase 0 (Now – 60 days) — Foundation**
- Publish this plan + updated investor materials.
- Launch public MCB email newsletter.
- Secure first 2–3 serious foundation conversations.
- Publish 2–3 sharp case studies from existing PDX-1i work.

**Phase 1 (Months 2–8) — Beachhead & Product**
- Introduce paid MCB tiers with clear free/paid split.
- Land at least one formal partnership with a local journalism org.
- Run first paid workshop.
- Reach 1,000+ engaged subscribers + meaningful revenue from product + grants.

**Phase 2 (Months 9–18) — Replicability**
- Hit $200k+ annual run-rate (mix of grants + product revenue).
- Begin packaging "Regional Accountability Desk" offering using the modular architecture.
- Document and selectively open-source non-sensitive local data models as a public good.

---

## Risks & Mitigations

- **Over-reliance on grants**: Build product revenue in parallel from day one.
- **Perception issues**: Lean hard into radical transparency (published calibration, funding disclosure, deterministic methods).
- **Data maintenance load**: Design for community contributions or paid maintenance contracts.
- **Low visibility**: Distribution partnerships are existential in the first 12 months.

---

## Why This Will Work

You already have the hardest parts:
- A genuinely differentiated technical system (deterministic + modular + human calibration).
- A real daily product shipping today.
- Deep local proof in a receptive market.
- Clear aesthetic and philosophical identity.

What is missing is disciplined go-to-market execution around distribution, audience ownership, and smart philanthropic + product revenue mix.

The architecture is the moat. The local focus is the beachhead. The hybrid funding model (Bellingcat-style) is the realistic path to sustainability while staying true to the mission.

---

**Immediate Next Steps (Recommended)**

1. Review and own this plan.
2. Launch the MCB email newsletter this week.
3. Identify and reach out to the top 5–7 funders already supporting Oregon Journalism Project / local accountability work.
4. Use the modular architecture story as the centerpiece of all fundraising and partnership conversations.

---

*This plan was produced through direct tool-driven research: codebase inspection, OSINT market data, Bellingcat financials, local Oregon journalism funding ecosystem mapping (Oregon Journalism Project, American Journalism Project, specific family foundations), competitive analysis, and review of current publication outputs.*

*All work executed on the dedicated branch with full tool audit trail.*
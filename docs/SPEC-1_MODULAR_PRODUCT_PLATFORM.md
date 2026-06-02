# SPEC-1: The Modular Product Platform for Open-Source Intelligence

**A deliberate architecture for building intelligence systems that scale as families of independent products — not monoliths.**

*Version 0.6 · Portland, Oregon · May 2026*

---

## The Fundamental Constraint

In national security, defense, critical infrastructure, and serious journalism, the scarce resource is not data.

It is **attention**.

Dozens of high-credibility sources publish every day. A single skilled analyst can meaningfully process perhaps 5–10 items in a day. The gap between published signal and human capacity is not a technology problem in the usual sense. It is a **triage and synthesis** problem.

Most organizations solve this by hiring more analysts or accepting that most material will never be read.

SPEC-1 takes a different position:

> **Automate the triage layer with deterministic, auditable logic. Reserve human judgment for the only place it cannot be replaced.**

This is not another "AI OSINT tool." It is an engineered platform whose central design decision is **modularity at the product level**.

---

## The Insight: Treat Outputs as Products

Traditional intelligence systems are built as pipelines that eventually produce "the report" or "the dashboard." Over time they become large, coupled codebases where adding a new type of output (psyop detection, legislative tracking, market signals, calibration drift analysis) requires invasive changes across the entire stack.

SPEC-1 inverts this.

Every distinct intelligence artifact the system produces is treated as a **first-class product**:

- Actionable Leads (`cls_leads`)
- Psychological Operation Detection (`cls_psyop`)
- Daily World Briefs (`cls_world_brief`)
- Human Verdict & Calibration Loops (`cls_verdicts` + `cls_calibration`)
- Legislative & Judicial Desk (`cls_leg_jud`)
- Portland Metro Political Intelligence Desk (`cls_pdx1`)

Each lives in its own package under `src/cls_<name>/`.

Each has a consistent, minimal contract:
- `schemas.py` — the canonical data model (dataclasses or Pydantic)
- `generator.py` / `producer.py` — the logic that creates the artifact
- `formatter.py` — presentation concerns
- `store.py` — persistence (the critical integration seam)

This is not accidental. It is the result of years of watching what happens when you *don't* do this.

---

## The Technical Pattern (Bulletproof by Design)

### 1. The Product Shape

A healthy SPEC-1 product is deliberately small at the boundary and rich on the inside when needed.

Simple products (leads, psyop, world briefs) are four or five files.

Complex products (PDX-1) contain sophisticated internal structure — `sources/`, `watch/`, `neutrality/`, `legislation/`, `publication/`, `anomaly.py`, `gates.py` — while still presenting a clean surface to the rest of the system.

The architecture explicitly supports both ends of the spectrum.

### 2. Dual-Write as the Universal Seam

No product is allowed to care deeply about storage.

```python
# From cls_psyop/store.py (and mirrored across products)
if db is not None:
    from cls_db.dual_write import DualWriter
    self._dual_writer = DualWriter(jsonl_path=..., db=db, table=...)
```

JSONL is always the source of truth. SQLite is best-effort and injected at construction time. Failure of the relational layer never breaks the product.

This single decision has proven more valuable than any amount of clever indexing.

### 3. Canonical Labels as Governance

All stringly-typed domain vocabulary lives in one place: `src/spec1_labels.py`.

Every product that needs `PRIORITY_HIGH`, `PSYOP_HIGH_RISK`, `VERIF_CORROBORATED`, or the new legislative domains (`congress.vote`, `judicial.ruling`, etc.) imports from here.

This is not pedantry. It is the only way a family of products can evolve together without semantic drift.

### 4. The Frozen Core + Explicit Write Surfaces

`src/spec1_engine/core/` (IDs, logging, the prompt library, the engine itself) is deliberately difficult to change.

Agents and contributors have clearly documented "free modification" zones (the product packages, the API routers, the signal/investigation layers, tests, docs) and "human approval required" zones.

This is not bureaucracy. It is the recognition that in a long-lived intelligence system, the core contracts are more valuable than any individual feature.

### 5. Per-Product API Surface

The FastAPI layer follows the same discipline:

`src/spec1_api/routers/`
- `leads.py`
- `psyop.py`
- `leg_jud.py`
- `publication.py`
- ...

No god router. No shared mutation of a central intelligence blob.

---

## The SPEC-1 Product Family (Current)

| Product              | Package         | Maturity | What It Produces                          | Internal Complexity |
|----------------------|-----------------|----------|-------------------------------------------|---------------------|
| Psyop Detection      | `cls_psyop`     | Mature   | Risk scores + evidence chains             | Medium              |
| Actionable Leads     | `cls_leads`     | Mature   | Prioritized, categorized opportunities    | Low                 |
| World Briefs         | `cls_world_brief` | Mature | Daily synthesized intelligence narrative  | Medium              |
| Human Feedback       | `cls_verdicts` + `cls_calibration` | Mature | Ground truth + drift detection          | Low                 |
| Legislative/Judicial | `cls_leg_jud`   | Active   | Structured desk briefs (federal + state)  | Medium              |
| Portland Metro Desk  | `cls_pdx1`      | Rapidly expanding | Entity graphs, voting patterns, disclosures, neutrality analysis, watch products | **High** (deliberately rich internals) |

This table is not marketing. It is the observable result of the architecture after multiple independent product expansions.

---

## Design Principles (The Actual Rules)

These are not aspirations. They are enforced in the codebase and in the contribution contract (`CLAUDE.md`).

1. **Products own their semantics.** No product reaches into another product's data model except through published stores.
2. **Persistence is a cross-cutting service, never a product concern.** Dual-write is injected, never imported at the top level of business logic.
3. **Labels are canonical.** New vocabulary must be proposed into `spec1_labels.py` before it proliferates.
4. **The core is frozen by default.** Changing it requires explicit human review and a version bump justification.
5. **Human judgment is sovereign.** Calibration and verdicts exist to make drift visible and decisions explicit. The system never auto-tunes.
6. **Presentation is part of the product contract.** The same rigor applied to scoring is applied to how the final artifact looks when it reaches a human.

These principles are what allow a 253-page directory tree of a real, running system to still feel coherent rather than accidental.

---

## Proof: The PDX-1 Expansion

The strongest evidence for the design is not in the simple products.

It is in `cls_pdx1` and `cls_leg_jud`.

In a few months, without modifying the frozen core, without touching the 4-gate signal scorer, without changing the dual-write contract, the system grew an entirely new intelligence product line:

- Bi-state (Oregon + Washington) legislative tracking
- Campaign finance (ORESTAR)
- Judicial disclosures and recusals
- Neutrality and tone analysis pipelines
- Watch lists for specific entities (utilities, transit, hospitals, corporations)
- Publication-quality output (newsletters, diagrams)

This is not a "module." It is a new desk.

The fact that it could be added at this speed and depth — while the original geopolitical/psyop/briefs system continued running — is the validation that the modular product model works at real scale.

---

## Why This Is Defensible

Most intelligence automation projects eventually become unmaintainable because they optimize for the first 18 months of features.

SPEC-1 optimizes for the next five years of *new products*.

**Risk reduction:**
- A bug in PDX-1 publication cannot break the daily world brief.
- A change in how legislative votes are scored cannot corrupt historical psyop evidence.
- Adding a new source adapter only touches the adapter registry and one product.

**Speed of innovation:**
- A new analyst can be productive in a single product package without understanding the entire pipeline.
- The calibration and verdict systems apply uniformly because they sit *above* the products.

**Human sovereignty preserved:**
- The calibration layer is deliberately descriptive. It surfaces drift. Humans decide what to do about it.
- Verdicts are append-only. Multiple reviewers are supported by design.

This combination — strong product boundaries + weak coupling at the persistence and API layers + explicit human override mechanisms — is rare.

---

## The Craft Layer

The system is not just architecturally disciplined. It is built by someone who cares about the experience of using it.

There is a dedicated aesthetic converter tool. Generated briefs have a consistent, high-signal visual language (dark terminal-inspired, credibility badges, gate pass/fail indicators, clean typography). The PDF pipeline runs as an out-of-process subprocess precisely so the core never takes a dependency on heavy native rendering libraries.

This is not decoration. In a system whose entire purpose is to compress attention, the final presentation layer is part of the product contract.

---

## Current State (v0.6)

- 253+ generated daily intelligence artifacts across multiple product lines
- Full dual-write persistence (JSONL + SQLite)
- Production FastAPI + APScheduler surface
- 12+ MCP tools exposed to Claude
- Active human feedback loops (verdicts + calibration)
- Live PDX-1 and legislative/judicial desks alongside the original geopolitical work
- ~30 test files, nearly 1,000 test functions, all external calls mocked
- Explicit governance that has survived multiple major expansions

---

## The Invitation

SPEC-1 is open source not because the author is generous, but because the only way to prove that this level of modularity works at national-security grade is to let serious people use it, break it, and extend it.

The architecture is the product.

If you are building intelligence systems — whether for government, industry, or journalism — the question is no longer "how do we add one more feed?"

The question is:

> "What would it look like if every new type of intelligence we wanted to produce could be added as a clean, independent product with its own lifecycle, without ever endangering the ones that already work?"

SPEC-1 is one answer to that question.

It is not finished. It is deliberately designed to never be finished in the old way.

---

**Further Reading**

- `CLAUDE.md` — The complete internal architecture and governance contract
- `docs/portfolio.md` + `docs/investor_outreach/INVESTOR_PITCH.md` — Market positioning
- `memory/context.md` — Live system state for contributors
- `src/cls_pdx1/` and `src/cls_leg_jud/` — The strongest proof of the model
- `src/cls_db/dual_write.py` + any `cls_*/store.py` — The integration pattern that makes everything else possible

---

*This document was synthesized on the `grok/award-winning-modular-vision` branch from the complete project context, including the full directory tree and architectural materials that were under active analysis on 30 May 2026.*

*It is intended to be printed at high quality (600 dpi, text-and-graphics) and read slowly.*
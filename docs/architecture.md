# SPEC-1 — Architecture Reference

> Authoritative reference for the system's structure, data flow, and governance rules.
> The full developer guide lives in [CLAUDE.md](../CLAUDE.md).

---

## Repository Layout

```
spec-1/
├── src/
│   ├── spec1_engine/        # Core OSINT pipeline (harvest → score → investigate → analyze)
│   │   ├── core/            # Frozen — schemas, IDs, logging, prompts
│   │   ├── signal/          # harvester, parser, scorer, complexity
│   │   ├── investigation/   # generator, verifier (Claude Haiku)
│   │   ├── intelligence/    # analyzer, store
│   │   ├── analysts/        # registry, credibility, discovery
│   │   ├── briefing/        # generator (Claude Sonnet) + writer + templates
│   │   ├── congressional/   # collector, parser, scorer, analyzer, cycle
│   │   ├── quant/           # collector, parser, scorer, analyzer, cycle
│   │   ├── workspace/       # persistent case files (case, tracker, researcher, CLI)
│   │   ├── tools/           # historical_briefs, calibration_propose, pdf_render
│   │   ├── cls_leads/       # re-export shim
│   │   ├── cls_psyop/       # re-export shim
│   │   ├── cls_world_brief/ # re-export shim
│   │   ├── api/             # legacy in-engine FastAPI mount
│   │   ├── app/cycle.py     # one-shot cycle entry point
│   │   └── main.py          # alternate entry point
│   │
│   ├── cls_osint/           # Extended OSINT adapters (feed, fara, congressional, narrative)
│   ├── cls_world_brief/     # Daily world intelligence brief
│   ├── cls_leads/           # Actionable intelligence leads
│   ├── cls_psyop/           # Psychological-operation detection
│   ├── cls_quant/           # Quantitative / market intelligence
│   ├── cls_verdicts/        # Phase 1 feedback: human ground truth
│   ├── cls_calibration/     # Phase 2 feedback: drift surfacing (descriptive only)
│   ├── cls_db/              # Dual-write persistence (JSONL + SQLite)
│   ├── spec1_api/           # Canonical FastAPI application + APScheduler
│   └── spec1_labels.py      # Canonical label/enum strings
│
├── tests/                   # 30 test files, 917 test functions
├── docs/                    # This folder — architecture, API, runbook, case study
├── memory/                  # Agent context, ADRs, session log
├── scripts/                 # Dev and operational scripts
├── db/                      # SQL migration files
├── mcp_server.py            # MCP server entry point
├── CHANGELOG.md
├── CLAUDE.md                # Developer + agent governance guide
└── pyproject.toml
```

---

## Data Flow

```
RSS / FARA / Congress / Narrative
         │
         ▼
   cls_osint.feed ───────────────────────────────────┐
         │                                            │
         ▼                                            ▼
  spec1_engine.signal                          cls_osint.adapters
  ├── harvester  → Signal[]                    ├── fara          → FaraRecord[]
  ├── parser     → ParsedSignal[]              ├── congressional → CongressRecord[]
  └── scorer     → Opportunity[]               └── narrative     → NarrativeRecord[]
         │                                            │
         ▼                                            ▼
  spec1_engine.investigation             cls_psyop.pipeline → PsyopScore[]
  ├── generator  → Investigation[]
  └── verifier   → Outcome[]
         │
         ▼
  spec1_engine.intelligence
  ├── analyzer   → IntelligenceRecord[]
  └── store      → spec1_intelligence.jsonl
         │
         ├──────────────┬──────────────────┬────────────────┐
         ▼              ▼                  ▼                ▼
  cls_world_brief   cls_leads      spec1_engine.briefing  cls_verdicts
  → WorldBrief[]    → Lead[]       → daily brief .md      (human input)
                                                                │
                                                                ▼
                                                       cls_calibration
                                                       → CalibrationReport
         │
         ▼
  cls_db.dual_write
  ├── JSONL (append-only, source of truth)
  └── SQLite (queryable index, can be rebuilt from JSONL)
         │
         ▼
  spec1_api (FastAPI + APScheduler)
  mcp_server.py (Claude MCP integration)
```

---

## 4-Gate Scoring System

Every signal must pass ALL four gates to become an `Opportunity`:

| Gate | Criterion | Default Threshold |
|------|-----------|-------------------|
| credibility | Source/analyst weight ≥ 0.5 | 0.5 |
| volume | Word count ≥ 50 | 50 words |
| velocity | Signal recency ≤ 48 hours | 48h |
| novelty | Not duplicate (hash-based) + keyword domain match | — |

Calibration drift across gates is surfaced by `cls_calibration` — **never auto-applied**.

---

## Key Data Models

| Model | Module | Description |
|-------|--------|-------------|
| `Signal` | `spec1_engine` | Raw RSS/OSINT item |
| `ParsedSignal` | `spec1_engine` | Cleaned, keywords/entities extracted |
| `Opportunity` | `spec1_engine` | Passed all 4 gates |
| `Investigation` | `spec1_engine` | Hypothesis + queries + analyst leads |
| `Outcome` | `spec1_engine` | Verified classification + confidence |
| `IntelligenceRecord` | `spec1_engine` | Final record with blended confidence |
| `AnalystRecord` | `spec1_engine` | Name, domains, credibility score |
| `OSINTRecord` | `cls_osint` | Generic extended OSINT item |
| `FaraRecord` | `cls_osint` | FARA filing |
| `CongressRecord` | `cls_osint` | Congressional record |
| `NarrativeRecord` | `cls_osint` | Influence-operation narrative |
| `WorldBrief` | `cls_world_brief` | Daily brief (headline, sections, sources) |
| `Lead` | `cls_leads` | Actionable intelligence lead |
| `PsyopScore` | `cls_psyop` | Psychological-operation detection score |
| `MarketBar` / `QuantSignal` | `cls_quant` | Market intelligence |
| `Verdict` | `cls_verdicts` | Human ground-truth (`correct\|incorrect\|partial\|unclear`) |
| `CalibrationReport` | `cls_calibration` | Descriptive drift report |

---

## Verification Outcome Classifications

| Outcome | Meaning |
|---------|---------|
| Corroborated | Evidence supports the hypothesis |
| Escalate | High-confidence, high-urgency finding |
| Investigate | Hypothesis plausible, more research needed |
| Monitor | Signal real but not yet actionable |
| Conflicted | Evidence is contradictory |
| Archive | Does not warrant further attention |

---

## Frozen Core — Governance

`src/spec1_engine/core/` is off-limits to ad-hoc edits.

- Agents may **import** from `core/` but may **not modify** it
- Changes require explicit human approval + semantic version bump
- `core/prompts/*.md` are the authoritative source for all prompt text

See [CLAUDE.md](../CLAUDE.md) for full governance rules and agent write surfaces.

---

## MCP Tools (mcp_server.py)

| Tool | Description |
|------|-------------|
| `run_cycle` | Trigger a full OSINT pipeline cycle |
| `get_signals` | Retrieve recent harvested signals |
| `get_intel` | Retrieve intelligence records |
| `get_leads` | Retrieve actionable leads |
| `get_brief` | Retrieve the latest world brief |
| `get_psyop` | Retrieve PsyOp detection results |
| `get_fara` | Retrieve FARA filings |
| `analyse_psyop` | Run PsyOp analysis on a signal |
| `get_stats` | System statistics |
| `file_verdict` | Record a human verdict on a record |
| `get_verdicts` | Retrieve filed verdicts |
| `get_calibration` | Get calibration drift report (descriptive only) |

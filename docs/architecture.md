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
├── tests/                   # 30 test files, ~825 collected tests (run `pytest --collect-only -q` for live count)
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

The system has two distinct execution layers: a canonical cycle that runs
automatically (on cron or on-demand via `/cycle/run`) and a set of operator
tools that the user invokes when they want a specific downstream artifact.

```
═════ Canonical cycle (automatic) ═════════════════════════════════════════════
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
         │
         ▼
  spec1_engine.investigation
  ├── generator  → Investigation[]   (Claude Haiku)
  └── verifier   → Outcome[]
         │
         ▼
  spec1_engine.intelligence
  ├── analyzer   → IntelligenceRecord[]
  └── store      → spec1_intelligence.jsonl   (append-only)


═════ Operator tools (manual, on-demand) ══════════════════════════════════════
  Each reads from spec1_intelligence.jsonl independently. None run inside the cycle.

  spec1_api /psyop/run                   → psyop_scores.jsonl
  spec1_api /brief/generate              → generated/briefs/spec1_brief_<date>.md
                                            (Claude Sonnet → cls_world_brief fallback)
  spec1_api /leads/generate              → leads.jsonl
  spec1_engine.tools.calibration_propose → calibration_report.{md,jsonl}
  spec1_engine.tools.historical_briefs   → backfill briefs for historical run_ids


═════ Feedback ════════════════════════════════════════════════════════════════
  cls_verdicts        — append-only human verdicts (correct|incorrect|partial|unclear)
                        on stored IntelligenceRecords
  cls_calibration     — descriptive drift report; never auto-applies tuning


═════ Persistence reality ═════════════════════════════════════════════════════
  JSONL is the source of truth across every store (append-only, immutable).
  cls_db.dual_write writes both JSONL and SQLite for:
    - cls_verdicts (verdicts.jsonl ↔ verdicts table)
    - cls_leads (leads.jsonl ↔ leads table)      [opt-in via db= kwarg]
    - cls_psyop (psyop_scores.jsonl ↔ psyop_scores table) [opt-in via db= kwarg]
  JSONL-only stores: intelligence/store.py, cls_world_brief, cls_osint adapters.

  Scalable read helpers (cls_db):
    - cls_db.cursor_reader.JSONLCursorReader — cursor-based forward pagination
      over large JSONL files without loading them entirely into memory.
    - cls_db.indexed_queries.IndexedQueryLayer — composable, limit-enforced
      queries over SQLite (wraps Repository).
    - DualWriter.read_chunked(limit) — iterate JSONL in chunks via cursor reader.
    - DualWriter.indexed_queries() — get an IndexedQueryLayer for the SQLite backend.
    - JsonlStore.read_chunk(offset, limit) — simple offset/limit slice for
      spec1_engine/intelligence/store.py.

  Migration / backfill:
    - spec1_engine.tools.backfill_jsonl_to_db — CLI to backfill any JSONL file
      into its SQLite table (idempotent; INSERT OR REPLACE semantics).
      Includes --verify mode for parity checks without writing.


═════ Surfaces ════════════════════════════════════════════════════════════════
  spec1_api (FastAPI + APScheduler)   — canonical lean cycle on cron + read endpoints
  mcp_server.py (Claude MCP)          — cycle + each operator tool exposed as a tool
```

---

## 4-Gate Scoring System

Every signal must pass ALL four gates to become an `Opportunity`.
Exact constants are in `src/spec1_engine/signal/scorer.py`.

| Gate | Criterion | Constant |
|------|-----------|----------|
| credibility | Source credibility score ≥ threshold | `CREDIBILITY_THRESHOLD = 0.60` |
| volume | Volume score ≥ threshold (tier-based; ≥30 words passes) | `VOLUME_THRESHOLD = 0.30` |
| velocity | Signal velocity score ≥ threshold (uses `signal.velocity`) | `VELOCITY_THRESHOLD = 0.0` |
| novelty | At least N keyword domain matches | `NOVELTY_THRESHOLD = 1` |

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

| Tool | Kind | Description |
|------|------|-------------|
| `run_cycle` | cycle | Trigger a full canonical OSINT cycle (intelligence records only) |
| `get_signals` | read | Retrieve recent harvested signals |
| `get_intel` | read | Retrieve intelligence records |
| `get_leads` | read | Retrieve actionable leads |
| `get_brief` | read | Retrieve the latest world brief |
| `get_psyop` | read | Retrieve PsyOp detection results |
| `get_fara` | read | Retrieve FARA filings |
| `analyse_psyop` | read | Run PsyOp analysis on arbitrary text |
| `get_stats` | read | System statistics |
| `file_verdict` | write | Record a human verdict on a record |
| `get_verdicts` | read | Retrieve filed verdicts |
| `get_calibration` | read | Get calibration drift report (descriptive only) |

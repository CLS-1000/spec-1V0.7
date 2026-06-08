# [ SPEC-1 INTELLIGENCE ENGINE ]

[![CI](https://github.com/mjlak1000/spec-1/actions/workflows/python-package.yml/badge.svg)](https://github.com/mjlak1000/spec-1/actions/workflows/python-package.yml)
[![Pages](https://github.com/mjlak1000/spec-1/actions/workflows/pages.yml/badge.svg)](https://mjlak1000.github.io/spec-1/)
[![Python](https://img.shields.io/badge/python-3.11%2B-white)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤-pink)](https://github.com/sponsors/mjlak1000)

```
INIT PID 1 ...
PYTHON 3.11+ DETECTED
LOADING 1,359 TESTS ... [OK]
PIPELINE STATUS: READY
// v0.6.0 · Portland OR · EVASTARARCANA
```

**Landing:** [mjlak1000.github.io/spec-1](https://mjlak1000.github.io/spec-1/) · **Dashboard:** [/ui](https://mjlak1000.github.io/spec-1/ui/)

---

## What Is This

SPEC-1 is an automated open-source intelligence engine. It harvests signals from authoritative sources, filters noise through a deterministic scoring pipeline, and hands the analyst exactly what matters — already classified, scored, and written up.

> **The bottleneck in intelligence work is not information. It is attention.**

Every day, credible reporting on national security, geopolitics, and regional power flows from dozens of authoritative sources. Most of it is noise. A small fraction is signal. Finding that fraction manually requires analyst hours that most operations don't have.

SPEC-1 automates the triage. The system handles the volume. The analyst handles the judgment.

---

## How It Works

Seven sequential stages. Each one fails independently — a dead RSS feed never stops the 06:00 cycle.

```
╔═══════════════════════════════════════════════════════════════════╗
║  [01 HARVEST] → [02 PARSE] → [03 SCORE] → [04 INVESTIGATE]        ║    
║                             │                                     ║
║                       4-Gate Filter                               ║
║                             │                                     ║
║               fail → /dev/null  pass → continue                   ║
║                             |                                     ║
║          [05 VERIFY] → [06 ANALYZE] → [07 STORE]                  ║
║                             │                                     ║
║                    Daily Brief + Leads                            ║
╚═══════════════════════════════════════════════════════════════════╝
```

| Stage | What Happens |
|---|---|
| `[01 HARVEST]` | RSS/Atom feeds fetched with SSL fallback and malformed XML recovery |
| `[02 PARSE]` | HTML stripped, keywords and entities extracted, word count measured |
| `[03 SCORE]` | Four independent gates evaluated — any failure drops the signal |
| `[04 INVESTIGATE]` | Hypothesis generated, research queries constructed, analyst leads identified |
| `[05 VERIFY]` | Three-tier LLM verification: Claude → Ollama → rule-based mock |
| `[06 ANALYZE]` | Confidence synthesized from source weight, analyst weight, and outcome |
| `[07 STORE]` | Dual-write: append-only JSONL (ground truth) + SQLite (query index) |

---

## The 4-Gate Scoring System

Every signal clears four independent gates or drops to `/dev/null`. No partial passes. No exceptions.

```
┌─────────────────┬────────────────────────────────────────────────┐
│ [CREDIBILITY]   │ Is this source trustworthy?                    │
│                 │ Source ratings are calibrated and unpublished. │
├─────────────────┼────────────────────────────────────────────────┤
│ [VOLUME]        │ Does this signal contain enough substance?     │
│                 │ Summaries and stubs are filtered out.          │
├─────────────────┼────────────────────────────────────────────────┤
│ [VELOCITY]      │ Is this signal fresh?                          │
│                 │ Intelligence value decays with time.           │
├─────────────────┼────────────────────────────────────────────────┤
│ [NOVELTY]       │ Does this signal touch high-value domains?     │
│                 │ Off-topic signals do not advance.              │
└─────────────────┴────────────────────────────────────────────────┘
```

Gate thresholds are calibrated through operational exposure and are not published. They represent the accumulated judgment of what separates actionable intelligence from background noise.

---

## What It Produces

Every cycle ships three things.

**World State Brief** — the daily publication. Executive summary, priority developments with trajectory assessments, domain briefings, story leads, 24-hour watch list. Black on white. Broadsheet format. Ships at 06:00 PT.

**Lead Intelligence Packets** — one per elevated signal. Expert context load, actor map, evidence checklist, three questions for named institutions, and an executable feed prompt. An analyst reads a packet and walks into any room already knowing more than the person across the table.

**Feed Prompts** — the ignition point. Each prompt is structured so that when an analyst pastes it into Claude with their source data, the output is original fact-based reporting — not a summary, not a rewrite. The system produces the intelligence that makes the intelligence.

---

## Modules

```
spec1_core/          Core 7-stage pipeline. Canonical namespace. Frozen — changes need sign-off.
spec1_api/           FastAPI service + APScheduler cron + MCP surface
cls_osint/           RSS, FARA, Congressional, Narrative adapters
cls_pdx1/            Portland Metro Intelligence — OLIS, ORESTAR, SEI, 911, entity graph
cls_legislative/     Cross-jurisdictional bill similarity via TF-IDF cosine
cls_psyop/           Narrative anomaly detection + influence operation scoring
cls_world_brief/     Daily brief generator + rule-based fallback
cls_leads/           Lead extraction with confidence scores and module routing
cls_verdicts/        Append-only analyst verdict collection
cls_calibration/     Drift detection + threshold adjustment proposals (human-decided)
cls_db/              Dual-write JSONL + SQLite persistence layer
```

---

## Data Sources

**National Security**
War on the Rocks · Cipher Brief · Just Security · RAND · Atlantic Council · Defense One · 38 North · NK News · Yonhap

**Regional — Portland Metro**
Oregon OLIS · ORESTAR · SEI · Portland 911 · TriMet · PGE · NW Natural · OHSU · Portland Water Bureau · PPB

**Federal**
DOJ FARA filings · Congressional bills, hearings, and disclosures

**Equities**
Defense primes · Cybersecurity vendors · Energy majors · Macro instruments

---

## Quick Start

```bash
git clone https://github.com/mjlak1000/spec-1.git
cd spec-1
pip install -e ".[dev]"
cp .env.example .env       # add your ANTHROPIC_API_KEY
make cycle                 # run one full pipeline cycle
```

```bash
make cycle        # harvest → score → brief → PDF
make run          # API server on 0.0.0.0:8000
make mcp          # MCP server for Claude Desktop integration
make brief        # generate brief from latest run_id
make leads        # extract leads from current records
make psyop        # score records for narrative anomalies
make workspace    # case management CLI
make test         # full test suite
```

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for investigation and brief generation |
| `SPEC1_DEV_MODE=true` | Skip Claude API, route verification to local Ollama |
| `SPEC1_STORE_PATH` | Append-only intelligence record store (JSONL) |
| `SPEC1_DB_PATH` | SQLite query index |
| `SPEC1_CRON_HOUR` | Daily cycle hour — default 6 (06:00 America/Los_Angeles) |
| `SPEC1_FEED_TIMEOUT` | Feed fetch timeout in seconds |
| `SPEC1_RUN_ON_START` | Execute cycle on API startup |
| `OLLAMA_MODEL` | Local model for Tier 2 LLM fallback |

---

## 3-Tier LLM Fallback

The verification stage never crashes the pipeline. Three tiers in sequence:

```
Tier 1: Claude Haiku    — production, low cost, fast
Tier 2: Local Ollama    — dev mode or API failure, zero cost
Tier 3: Rule-based mock — always available, deterministic
```

Set `SPEC1_DEV_MODE=true` to bypass Tier 1. Every LLM call is logged to `logs/llm_fallback.jsonl` with tier, latency, and cost estimate.

---

## API

```
GET  /health              Health check + pipeline status
POST /cycle/run           Trigger one cycle immediately
GET  /cycle/status        Last cycle metadata and stats
GET  /signals             Harvested signals with gate scores
GET  /intel               Intelligence records
GET  /leads               Extracted leads with confidence scores
POST /leads/generate      Generate leads from current records
GET  /brief/latest        Latest World State Brief
GET  /brief/{date}        Brief by date or run_id
POST /psyop/analyse       Score arbitrary text for narrative anomalies
GET  /fara                FARA filing records
GET  /verdicts            Analyst verdicts
POST /verdicts            File a verdict on a record
GET  /calibration/report  Drift detection report
```

Full API reference: [docs/api.md](docs/api.md)

---

## MCP Integration

SPEC-1 exposes a Model Context Protocol server for Claude Desktop and Claude Code integration.

```bash
make mcp   # starts mcp_server.py over stdio
```

Tools: `run_cycle` · `get_signals` · `get_intel` · `get_leads` · `get_brief` · `get_psyop` · `get_fara` · `analyse_psyop` · `get_stats` · `file_verdict` · `get_verdicts` · `get_calibration`

Claude Desktop config:

```json
{
  "mcpServers": {
    "spec-1": {
      "command": "python",
      "args": ["/path/to/spec-1/mcp_server.py"],
      "cwd": "/path/to/spec-1"
    }
  }
}
```

---

## Architectural Invariants

These do not change without operator sign-off and a version bump.

| Invariant | Rule |
|---|---|
| Append-only store | Records are never overwritten or deleted |
| Single-writer rule | One writer per namespace, enforced with threading lock |
| Failure-first | Every stage logs and continues — nothing crashes the pipeline |
| Four-gate filter | All four gates must pass — no bypass, no partial credit |
| Run ID | Single source of truth for every cycle |
| Dual-write | JSONL is ground truth. SQLite is the query layer. |
| Calibration | Drift is surfaced, never auto-applied — humans tune thresholds |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Brief not generated | Invalid or missing API key | Check `.env`; rule-based fallback activates automatically |
| `make cycle` hangs | Network timeout or unreachable feed | Increase `SPEC1_FEED_TIMEOUT` |
| No signals through gates | Thresholds need calibration | Run `GET /calibration/report`; file verdicts to inform proposals |
| SQLite locked | Concurrent writes or stale process | Restart API; check for orphaned processes |
| Pipeline crashes | Unhandled exception in a stage | This should not happen — file an issue with the full stack trace |

---

## Contributing

Bug reports, new data source adapters, and gate calibration feedback are welcome.

**Bug Reports** — open a GitHub issue with reproducible steps, logs, and stack trace.

**New Data Sources** — add feed to `cls_osint/sources.py`, register in the feed registry, implement adapter if specialized logic is required.

**Gate Calibration** — file verdicts on signals via `POST /verdicts`. The calibration module surfaces drift. Threshold proposals go to `GET /calibration/report`. Human decides whether to apply.

**Development**
```bash
pip install -e ".[dev]"
make test        # must pass before any PR
ruff check src/  # linting
```

See [DESIGN_INTENT.md](DESIGN_INTENT.md) for canonical system intent — agents read this first.

---

## Sponsors

SPEC-1 is independent, open-source intelligence infrastructure built and operated by EVASTARARCANA LLC in Portland, OR.

If this project saves you analyst hours, inspires your own work, or you just want to see what comes next — consider sponsoring development.

[![Sponsor](https://img.shields.io/badge/Sponsor-❤-pink)](https://github.com/sponsors/mjlak1000)

Sponsors get early access to **World State Brief** issues and the **PSYCHE-OPS** column — original intelligence analysis produced by the system and reviewed by a human analyst before publication.

---

## Reference

| Document | Purpose |
|---|---|
| [DESIGN_INTENT.md](DESIGN_INTENT.md) | Canonical architecture intent — read before making changes |
| [CLAUDE.md](CLAUDE.md) | Agent governance and developer rules |
| [AUDIT_NOTES.md](AUDIT_NOTES.md) | Architecture audit findings |
| [docs/api.md](docs/api.md) | Full HTTP API reference |
| [docs/architecture.md](docs/architecture.md) | System design and data models |
| [docs/quickstart.md](docs/quickstart.md) | Getting started guide |
| [docs/runbook.md](docs/runbook.md) | Operational procedures |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

```
SPEC-1 // EVASTARARCANA · Portland OR
CLASSIFICATION: UNCLASSIFIED
```

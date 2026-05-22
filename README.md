# SPEC-1 Intelligence Engine

[![CI](https://github.com/mjlak1000/spec-1/actions/workflows/python-package.yml/badge.svg)](https://github.com/mjlak1000/spec-1/actions/workflows/python-package.yml)
[![Pages](https://github.com/mjlak1000/spec-1/actions/workflows/pages.yml/badge.svg)](https://mjlak1000.github.io/spec-1/)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

**Landing:** [mjlak1000.github.io/spec-1](https://mjlak1000.github.io/spec-1/) · **Dashboard:** [/ui](https://mjlak1000.github.io/spec-1/ui/)

## Portfolio entry points

- **Landing page:** [mjlak1000.github.io/spec-1](https://mjlak1000.github.io/spec-1/)
- **Interactive dashboard:** [mjlak1000.github.io/spec-1/ui](https://mjlak1000.github.io/spec-1/ui/)
- **Portfolio summary:** [docs/portfolio.md](docs/portfolio.md)
- **Case study (engineering decisions):** [docs/case_study.md](docs/case_study.md)

The bottleneck in intelligence work is attention, not information. SPEC-1 handles the triage: it monitors a curated set of authoritative national security sources continuously, scores every new signal through a four-gate deterministic filter, and hands only the survivors to Claude for investigation and verification. What reaches the analyst is already classified, scored, and structured — ready for a decision, not a digest.

**Canonical cycle** — runs automatically on cron or on-demand via `POST /cycle/run`. Produces one artifact: append-only `IntelligenceRecord` objects in `spec1_intelligence.jsonl`.

**Operator tools** — invoked deliberately. Briefs, leads, psyop scores, and calibration reports each read from the intelligence store independently. None runs silently inside the cycle. The separation is the architecture: the cycle ships a trustworthy, auditable core; downstream artifacts are explicit operator decisions, never side effects.

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture, data flow, models |
| [docs/api.md](docs/api.md) | HTTP API reference |
| [docs/runbook.md](docs/runbook.md) | Operational procedures |
| [docs/portfolio.md](docs/portfolio.md) | Project overview for stakeholders |
| [docs/case_study.md](docs/case_study.md) | Design decisions and engineering rationale |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [memory/decisions.md](memory/decisions.md) | Architecture Decision Records |
| [CLAUDE.md](CLAUDE.md) | Developer and agent governance |

## Architecture

```
═══ Canonical cycle (automatic) ═══════════════════════════════════════
RSS / FARA / Congress / Narrative
        │
        ▼
  cls_osint.feed ─────────── cls_osint.adapters (fara, congressional, narrative)
        │
        ▼
  spec1_core  (harvest → parse → score → investigate → verify → analyze)
        │
        ▼
  IntelligenceRecord  →  spec1_intelligence.jsonl  (append-only)

═══ Operator tools (manual, on-demand) ════════════════════════════════
  make psyop         → generated/psyop_scores.jsonl
  make brief         → generated/briefs/*.md
  make leads         → generated/leads.jsonl
  make calibration   → generated/calibration_report.*
  make backfill      → briefs for historical run_ids

═══ Surfaces ══════════════════════════════════════════════════════════
  spec1_api   (FastAPI HTTP + APScheduler daily cron)
  mcp_server  (MCP tools for Claude — cycle + operator tools)

═══ Persistence ═══════════════════════════════════════════════════════
  JSONL   : source of truth, append-only (every store)
  SQLite  : queryable index, rebuildable from JSONL
```

## Quick Start

```bash
# Note: pip install -e ".[dev]" has a known sgmllib3k build issue (feedparser transitive).
# Workaround: use `uv pip install --system -e ".[dev]"` or install with uv.
# See FALLBACK_SETUP.md for details.

bash scripts/setup_dev.sh

# Or manually:
uv pip install --system -e ".[dev]"
cp .env.example .env  # set ANTHROPIC_API_KEY
```

```bash
make cycle        # one-shot intelligence cycle (records + brief + workspace)
make run          # API server → http://localhost:8000
make mcp          # MCP server (Claude integration)
make brief        # generate brief from latest run_id
make leads        # derive Lead objects from intelligence records
make psyop        # score every record for psyop patterns
make calibration  # calibration drift report from intel + verdicts
make workspace    # workspace CLI (case management)
make test         # full test suite
make help         # all commands
```

## Environment

```bash
cp .env.example .env  # edit — set ANTHROPIC_API_KEY at minimum
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for investigation and briefing |
| `SPEC1_STORE_PATH` | `spec1_intelligence.jsonl` | Intelligence record store |
| `SPEC1_DB_PATH` | `spec1.db` | SQLite database path |
| `SPEC1_API_HOST` | `0.0.0.0` | API bind address |
| `SPEC1_API_PORT` | `8000` | API port |
| `SPEC1_CRON_HOUR` | `6` | Scheduled cycle hour (24h) |
| `SPEC1_TIMEZONE` | `America/Los_Angeles` | Scheduler timezone |
| `SPEC1_FEED_TIMEOUT` | `15` | Feed fetch timeout (seconds) |
| `SPEC1_RUN_ON_START` | `false` | Run one cycle immediately on API startup |

## Modules at a Glance

**Core Intelligence Pipeline**
- `spec1_engine` — canonical 7-stage cycle (harvest → parse → score → investigate → verify → analyze → store)
- `cls_osint` — RSS/FARA/Congressional/Narrative adapters with feed registry
- `spec1_api` — FastAPI service with scheduler, dual-write persistence, MCP server

**Intelligence Products & Analysis**
- `cls_world_brief` — Daily structured intelligence brief (Claude Sonnet writer, rule-based fallback)
- `cls_leads` — Actionable leads extracted from scored records
- `cls_psyop` — Psychological-operation pattern detection and scoring
- `cls_leg_jud` — Legislative and judicial desk tracking
- `cls_pdx1` — PDX-1i Metro Citizens Brief (Portland bi-state metro elected officials, entities, districts)
- `cls_db` — Append-only JSONL + SQLite dual-write persistence

**Intelligence Operations**
- `spec1_engine.workspace` — Case management CLI for investigation tracking
- `spec1_engine.app.publishers.x` — X/Twitter thread publication (with idempotency log)
- `spec1_engine.llm` — Three-tier fallback client (Claude Sonnet → Ollama → rule-based)
- `cls_verdicts` — Human ground-truth verdict collection (append-only)
- `cls_calibration` — Drift detection and threshold proposal (descriptive only, human-decided)

**Data Sources**

- **RSS Feeds:** War on the Rocks, Cipher Brief, Just Security, RAND, Atlantic Council, Defense One
- **OSINT Adapters:** FARA (Foreign Agents Registration Act) filings, Congressional records (bills, hearings), Narrative/influence-operation tracking, State-level political data (Oregon OLIS, ORESTAR; Washington PDC)
- **Equities Watchlist:** Defense primes, cybersecurity vendors, energy majors, macro instruments (via yfinance)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /signals | Latest harvested signals |
| POST | /signals/ingest | Ingest a signal manually |
| GET | /intel | Intelligence records |
| GET | /leads | Actionable leads |
| POST | /leads/generate | Generate leads from current records |
| GET | /brief | Latest world brief |
| GET | /brief/latest | Latest brief (alias) |
| GET | /brief/history | All briefs, newest first |
| GET | /brief/index | Brief index (run_ids + dates) |
| GET | /brief/{date} | Brief by date or run_id |
| POST | /brief/generate | Generate brief for a run_id |
| GET | /psyop | PsyOp detections |
| POST | /psyop/analyse | Score text for psyop patterns |
| POST | /psyop/run | Score all records for psyop patterns |
| GET | /fara | FARA filings |
| GET | /verdicts | Filed verdicts |
| GET | /verdicts/{record_id} | Verdicts for a specific record |
| POST | /verdicts | File a verdict |
| GET | /calibration/report | Calibration drift report (descriptive) |
| GET | /calibration/proposals | Suggested threshold adjustments |
| GET | /cycle/status | Last cycle status |
| POST | /cycle/run | Trigger one canonical cycle |
| GET | /publication/latest | Download latest publication |
| GET | /publication/list | List all publications |
| POST | /publication/generate | Generate a new publication |
| GET | /publication/{filename} | Download publication by filename |
| GET | /workspace/cases | List investigation cases |
| POST | /workspace/cases | Open a new case |
| GET | /workspace/cases/{case_id} | Get case detail |
| POST | /workspace/cases/{case_id}/close | Close a case |

> Routes `GET /nodes/{node_id}/signal` and `POST /ingest/signal` are conditionally mounted when `SPEC1_POLITICAL_WEB_ENABLED=true`.

The canonical cycle produces intelligence records only. Briefs, leads, and psyop scores require their operator tools — see Quick Start.

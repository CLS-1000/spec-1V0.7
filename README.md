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
  spec1_engine  (harvest → parse → score → investigate → verify → analyze)
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
bash scripts/setup_dev.sh

# Or manually:
pip install -e ".[dev]"
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
| `SPEC1_QUANT_ENABLED` | `false` | Enable quantitative market signal pipeline |

## Key Sources

**RSS Feeds**
- War on the Rocks, Cipher Brief, Just Security, RAND, Atlantic Council, Defense One

**OSINT Adapters**
- FARA (Foreign Agents Registration Act) filings
- Congressional records (bills, hearings)
- Narrative / influence-operation tracking

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /signals | Latest harvested signals |
| GET | /intel | Intelligence records |
| GET | /leads | Actionable leads |
| POST | /leads/generate | Generate leads from current records |
| GET | /brief | Latest world brief |
| GET | /psyop | PsyOp detections |
| POST | /psyop/run | Score all records for psyop patterns |
| GET | /fara | FARA filings |
| GET | /verdicts | Filed verdicts |
| POST | /verdicts | File a verdict |
| GET | /calibration/report | Calibration drift report (descriptive) |
| GET | /calibration/proposals | Suggested threshold adjustments |
| POST | /cycle/run | Trigger one canonical cycle |

The canonical cycle produces intelligence records only. Briefs, leads, and psyop scores require their operator tools — see Quick Start.

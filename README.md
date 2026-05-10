# SPEC-1 Intelligence Engine

SPEC-1 is a real-time open-source intelligence (OSINT) platform.

**Canonical cycle (automatic):** harvest signals from RSS feeds, FARA filings, congressional records, and narrative sources → 4-gate scoring → Claude-driven investigation + verification → IntelligenceRecord persisted to append-only JSONL.

**Operator tools (manual):** psyop scoring (`make psyop`), daily brief generation with rule-based fallback (`make brief`), actionable lead derivation (`make leads`), and calibration drift reports (`make calibration`). Each reads from the intelligence JSONL and writes its own artifact — none run automatically inside the cycle.

The split is deliberate: the cycle ships a small, trustworthy core; downstream artifacts are explicit operator decisions, not silent side effects.

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture, data flow, data models |
| [docs/api.md](docs/api.md) | HTTP API endpoint reference |
| [docs/runbook.md](docs/runbook.md) | Operational procedures and troubleshooting |
| [docs/portfolio.md](docs/portfolio.md) | Project overview for stakeholders |
| [docs/case_study.md](docs/case_study.md) | Design decisions and engineering rationale |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [memory/decisions.md](memory/decisions.md) | Architecture Decision Records (ADRs) |
| [CLAUDE.md](CLAUDE.md) | Developer and agent governance guide |

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
  make psyop                          → psyop_scores.jsonl
  make brief                          → generated/briefs/*.md
  make leads                          → leads.jsonl
  spec1_engine.tools.calibration_propose → calibration_report.* (make calibration)
  spec1_engine.tools.historical_briefs   → backfill briefs      (make backfill)

═══ Surfaces ══════════════════════════════════════════════════════════
  spec1_api  (FastAPI HTTP server + APScheduler)
  mcp_server (MCP tools for Claude — cycle + each operator tool)

═══ Persistence ═══════════════════════════════════════════════════════
  JSONL  : source of truth, append-only (every store)
  SQLite : queryable index, rebuildable from JSONL
  cls_db.dual_write currently writes both for verdicts only;
  every other store is JSONL-only today.
```

## Quick Start

```bash
# Install and verify
bash scripts/setup_dev.sh

# Or manually:
pip install -e ".[dev]"
cp .env.example .env  # then set ANTHROPIC_API_KEY
```

```bash
make cycle        # one-shot intelligence cycle (rich CLI path; produces records + brief + workspace updates)
make run          # API server → http://localhost:8000  (canonical lean cycle on schedule)
make mcp          # MCP server (Claude integration)
make brief        # operator tool — generate brief from latest run_id (Claude + rule-based fallback)
make leads        # operator tool — derive Lead objects from intelligence records
make psyop        # operator tool — score every record for psyop patterns
make calibration  # operator tool — calibration drift report from intel + verdicts
make workspace    # workspace CLI (case management)
make test         # full test suite
make help         # all available commands
```

## Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY
```

Key variables:

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
| `SPEC1_RUN_ON_START` | `false` | If `true`, run one cycle immediately on API startup |
| `SPEC1_POLITICAL_WEB_ENABLED` | `false` | If `true`, mount `/portland-web`, `nodes`, and `ingest` routers (off by default) |
| `SPEC1_QUANT_ENABLED` | `false` | Documented for the quant CLI; not currently read by the canonical cycle |

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
| GET | /leads | Actionable leads (read-only; populate via `make leads`) |
| POST | /leads | Create a lead |
| GET | /brief | Latest world brief (read-only; populate via `make brief`) |
| GET | /psyop | PsyOp detections (read-only; populate via `make psyop`) |
| GET | /fara | FARA filings |
| GET | /verdicts | Filed verdicts |
| POST | /verdicts | File a verdict |
| GET | /calibration | Calibration drift report (descriptive) |
| POST | /cycle/run | Trigger one canonical lean cycle (intelligence records only) |

The canonical cycle endpoint produces only intelligence records. Briefs, leads, and psyop scores are populated by the corresponding operator tools — see Quick Start.

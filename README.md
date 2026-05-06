# SPEC-1 Intelligence Engine

SPEC-1 is a real-time open-source intelligence (OSINT) platform that harvests signals from
RSS feeds, FARA filings, congressional records, and narrative sources; scores them through a
4-gate pipeline; detects psychological operations; generates actionable leads and world briefs;
and persists everything to JSONL and SQLite.

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
RSS/FARA/Congress/Narrative
        │
        ▼
  cls_osint.feed ──────── cls_osint.adapters (fara, congressional, narrative)
        │
        ▼
  spec1_engine  (harvest → parse → score → investigate → verify → analyze)
  ├── analysts      (credibility weighting, source discovery)
  ├── briefing      (daily brief generation)
  ├── quant         (market signal analysis)
  └── workspace     (case tracking, researcher CLI)
        │
        ├── cls_psyop       (psychological operation detection)
        ├── cls_quant       (market intelligence)
        ├── cls_leads       (actionable leads)
        ├── cls_world_brief (daily intelligence brief)
        └── cls_db          (dual-write: JSONL + SQLite)
                │
                ▼
          spec1_api  (FastAPI HTTP server)
          mcp_server (MCP tools for Claude)
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
make cycle      # one-shot intelligence cycle
make run        # API server → http://localhost:8000
make mcp        # MCP server (Claude integration)
make workspace  # workspace CLI (case management)
make test       # full test suite
make help       # all available commands
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
| `SPEC1_QUANT_ENABLED` | `false` | Enable quantitative market pipeline |

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
| POST | /leads | Create a lead |
| GET | /brief | Latest world brief |
| GET | /psyop | PsyOp detections |
| GET | /fara | FARA filings |
| POST | /cycle/run | Trigger a full cycle |

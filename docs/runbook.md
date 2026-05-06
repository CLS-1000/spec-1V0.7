# SPEC-1 Operational Runbook

Procedures for running, maintaining, and debugging SPEC-1 in production.

---

## Daily Operations

### Check last cycle output

```bash
# Latest brief
cat briefs/spec1_brief_latest.md

# Intelligence records from last run
tail -n 20 spec1_intelligence.jsonl | python -m json.tool

# API health
curl http://localhost:8000/health
```

### Trigger a manual cycle

```bash
# Via CLI (no server required)
python -m spec1_engine.app.cycle

# Via API
curl -X POST http://localhost:8000/cycle/run

# Via Makefile
make cycle
```

### Check scheduler status

```bash
curl http://localhost:8000/health
# Look for: "scheduler": "running"
```

---

## Starting Services

### API server (canonical)

```bash
make run
# or
PYTHONPATH=src python -m spec1_api.main
```

### MCP server (Claude integration)

```bash
make mcp
# or
PYTHONPATH=src python mcp_server.py
```

---

## Development

### Install and run tests

```bash
make install    # pip install -e ".[dev]"
make test       # pytest tests/ -v --tb=short
make lint       # flake8 src/ tests/
```

### Run the quantitative market signal pipeline

```bash
pip install -e ".[dev,quant]"
PYTHONPATH=src python -m spec1_engine.quant.cycle
# or
make install-quant && scripts/run_cycle.sh --quant
```

### Environment setup

```bash
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY
make install
```

---

## Persistence

### JSONL files (source of truth)

| File | Contents |
|------|----------|
| `spec1_intelligence.jsonl` | Intelligence records |
| `verdicts.jsonl` | Human verdicts |
| `leads.jsonl` | Actionable leads |
| `world_briefs.jsonl` | Daily world briefs |
| `psyop_scores.jsonl` | PsyOp detection results |

All JSONL files are append-only. Never edit them manually.

### Rebuild SQLite from JSONL

```bash
PYTHONPATH=src python -m cls_db.migrate
# Then restart the API to repopulate
```

### Run schema migrations

```bash
PYTHONPATH=src python -m cls_db.migrate
```

---

## Briefing

### Backfill briefs for historical run_ids

```bash
make backfill
# or
PYTHONPATH=src python -m spec1_engine.tools.historical_briefs
```

### Generate a calibration proposal report

```bash
make calibration
# or
PYTHONPATH=src python -m spec1_engine.tools.calibration_propose \
    --intel spec1_intelligence.jsonl \
    --verdicts verdicts.jsonl \
    --out-dir generated/
```

---

## Filing Verdicts

Verdicts are append-only. Multiple verdicts per record are allowed.

```bash
# Via MCP (Claude session)
# → Use the file_verdict tool

# Via API
curl -X POST http://localhost:8000/verdicts \
  -H "Content-Type: application/json" \
  -d '{"record_id": "rec_...", "kind": "correct", "reviewer": "handle", "notes": ""}'
```

Valid `kind` values: `correct`, `incorrect`, `partial`, `unclear`

---

## Workspace (Case Management)

```bash
make workspace
# or
PYTHONPATH=src python -m spec1_engine.workspace
```

---

## Troubleshooting

### API won't start

1. Check `.env` exists and `ANTHROPIC_API_KEY` is set
2. Check port 8000 isn't in use: `lsof -i :8000`
3. Run `make install` to ensure dependencies are current

### Cycle produces no records

1. Check feed connectivity: `curl https://warontherocks.com/feed/`
2. Check API key: `python scripts/anthropic_smoke.py`
3. Lower velocity threshold temporarily (signals may be stale)

### Brief is rule-based (no Claude output)

The briefing module falls back silently on API errors. Check:
1. `ANTHROPIC_API_KEY` is valid and has quota
2. `python scripts/anthropic_smoke.py`

### SQLite and JSONL are out of sync

The JSONL is the source of truth. Rebuild SQLite:

```bash
rm spec1.db
PYTHONPATH=src python -m cls_db.migrate
```

---

## Generated Artifacts

Scheduled cycle briefs are written to `briefs/` (gitignored at root).
One-off exports and reports go to `generated/` (also gitignored). Never commit either to `main`.

```
briefs/            # Brief .md files written by the cycle and historical_briefs tool
generated/
├── reports/       # Calibration proposal reports
└── exports/       # One-off data exports
```

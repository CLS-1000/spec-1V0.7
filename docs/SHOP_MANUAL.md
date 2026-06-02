# SPEC-1 Shop Manual

> The single workshop-bench reference for an operator who needs to run, observe, troubleshoot, and extend SPEC-1. This document does not replace the deep-dive docs (`docs/architecture.md`, `docs/api.md`, `docs/runbook.md`) — it aggregates the operational surface in one place and links out for depth.

**Companion audit:** [`docs/ACCESS_AUDIT.md`](ACCESS_AUDIT.md) — every command, endpoint, MCP tool, model, and env var enumerated with efficiency findings.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Quickstart](#3-quickstart)
4. [Commands](#4-commands)
5. [HTTP API](#5-http-api)
6. [MCP Server](#6-mcp-server)
7. [Models](#7-models)
8. [Environment Variables](#8-environment-variables)
9. [Workflows / Cookbook](#9-workflows--cookbook)
10. [File Layout](#10-file-layout)
11. [Troubleshooting](#11-troubleshooting)
12. [Glossary](#12-glossary)

---

## 1. Overview

SPEC-1 is an open-source intelligence (OSINT) engine that continuously harvests signals from RSS feeds, FARA filings, congressional records, and narrative sources; scores them through a deterministic 4-gate pipeline; runs Claude-assisted investigation and verification on the survivors; and produces three operator-facing artifacts:

1. **Append-only `IntelligenceRecord` stream** (`spec1_intelligence.jsonl`) — the canonical cycle output.
2. **Operator tools** invoked on-demand — daily world briefs, actionable Leads, psyop scoring, calibration drift reports.
3. **A dashboard** (`spec1_ui.html`) — reads the stores over HTTP and exposes the workbench of executable actions.

The cycle runs automatically on cron (`SPEC1_CRON_HOUR`/`SPEC1_CRON_MINUTE`) or on-demand via `POST /cycle/run`. Operator tools are explicit decisions, not cycle side-effects — this separation is the architecture.

---

## 2. Architecture

```
═══ Canonical cycle (automatic) ═══════════════════════════════════════
  RSS  /  FARA  /  Congress  /  Narrative
                    │
                    ▼
            cls_osint.feed
                    │            adapters: fara, congressional,
                    ▼            narrative, verifier
            spec1_core
                    │   (harvest → parse → 4-gate score
                    │              → investigate → verify
                    ▼              → analyze)
            IntelligenceRecord ──► spec1_intelligence.jsonl  (append-only JSONL)
                    │
                    └──► SQLite dual-write (cls_db, optional)

═══ Operator tools (manual, on-demand) ════════════════════════════════
  make brief        ──► generated/spec1_brief_*.md   (Claude Sonnet, rule-based fallback)
  make leads        ──► leads.jsonl
  make psyop        ──► generated/psyop_scores.jsonl
  make calibration  ──► generated/calibration_*.md   (descriptive, no auto-tune)
  make backfill     ──► fills historical brief gaps
  make workspace    ──► interactive case-file CLI

═══ External surfaces ════════════════════════════════════════════════
  FastAPI server  (port 8000)  ─►  17 routers, 41 routes
  MCP server      (stdio)      ─►  15 JSON-RPC tools for Claude
  spec1_ui.html   (static)     ─►  workbench dashboard
```

**Module map:**

| Module | Role |
|--------|------|
| `spec1_engine` | Frozen core pipeline (`harvest → parse → score → investigate → analyze`); contains briefing, congressional, quant, workspace, analyst-credibility, and a `tools/` CLI subpackage |
| `cls_osint` | Extended OSINT adapters: FARA, congressional, narrative, feed fetchers |
| `cls_world_brief` | Daily world brief schemas / producer / formatter / store |
| `cls_leads` | Actionable lead derivation from intel records |
| `cls_psyop` | Psyop pattern detection: patterns, scorer, pipeline, evidence chain |
| `cls_verdicts` | Append-only human verdicts (Phase 1 feedback loop) |
| `cls_calibration` | Descriptive drift reports + proposal generator (Phase 2 feedback loop) |
| `cls_db` | SQLite dual-write layer (signals, records, leads, briefs, psyop, verdicts, calibration) |
| `cls_pdx1` | Portland-1 regional adapter (separate signal namespace) |
| `spec1_api` | FastAPI app, scheduler, auth, routers, webhooks |
| `spec1_analytics` | Read-only analytics layer over the stores |
| `spec1_core` | Engine internals and LLM client (`llm/fallback_client.py` — Anthropic→Ollama tier chain) |

Deep dive: [`docs/architecture.md`](architecture.md).

---

## 3. Quickstart

```bash
# 1. install
cd ~/spec-1
make install                       # equivalent to pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-…  # required for briefing + investigation + workspace + pdx1

# 2. run one cycle (writes to spec1_intelligence.jsonl)
make cycle

# 3. view the dashboard
make run                           # starts FastAPI on http://127.0.0.1:8000
open spec1_ui.html                 # static HTML — talks to localhost:8000
```

That is enough to produce a working IntelligenceRecord stream and inspect it. Operator tools (`brief`, `leads`, `psyop`, `calibration`) are explicit follow-ons — run them when you want their artifact.

Deeper start: [`docs/quickstart.md`](quickstart.md).

---

## 4. Commands

### 4.1 Makefile targets

| Target | What it does | When to use |
|--------|--------------|-------------|
| `make install` | `pip install -e ".[dev]"` | First run / dependency change |
| `make test` | Full pytest suite (`-v --tb=short`) | Before commit, in CI |
| `make test-fast` | pytest `-x -q`, stop at first failure | Local feedback loop |
| `make test-cov` | pytest with coverage report | Coverage triage |
| `make lint` | `flake8` (max-line-length=120) | Style audit |
| `make run` | Start FastAPI on port 8000 | Serve the dashboard / external clients |
| `make mcp` | Start MCP server on stdio | Used by Claude Code or any MCP client |
| `make cycle` | One-shot intelligence cycle | Manual run; cron handles automatic |
| `make backfill` | Backfill briefs for historical `run_id`s | Recover from cron outages |
| `make calibration` | Calibration drift report → `generated/` | Periodic audit of scoring accuracy |
| `make brief` | Daily brief for latest `run_id` | On-demand intel digest |
| `make leads` | Derive Leads from intel records | Operator workflow |
| `make psyop` | Score every intel record for psyop patterns | Bulk re-scoring |
| `make workspace` | Open workspace CLI (interactive) | Case-file investigation |
| `make clean` | Remove `__pycache__` and `.pytest_cache` | Housekeeping |

### 4.2 `python -m` entry points

Each Makefile target above is a thin wrapper. The underlying invocations:

```
python -m spec1_api.main                              # API server (make run)
python  mcp_server.py                                 # MCP server   (make mcp)
python -m spec1_engine.app.cycle                      # canonical cycle (make cycle)
python -m spec1_engine.tools.historical_briefs        # backfill
python -m spec1_engine.tools.calibration_propose \
        --intel spec1_intelligence.jsonl \
        --verdicts verdicts.jsonl \
        --out-dir generated/                          # calibration
python -m spec1_engine.tools.generate_brief           # daily brief
python -m spec1_engine.tools.generate_leads           # leads
python -m spec1_engine.tools.run_psyop                # psyop scoring
python -m spec1_engine.workspace                      # workspace CLI
python -m spec1_engine.main                           # alt entry
```

All assume `PYTHONPATH=src` (the Makefile sets it; set it manually outside).

### 4.3 Shell scripts

`scripts/run_cycle.sh` — wrapper for `make cycle` with env loading.
`scripts/setup_dev.sh` — one-shot dev environment bootstrap.
`scripts/anthropic_smoke.py` — verify your `ANTHROPIC_API_KEY` is live.
`tools/manual_publisher.py` — top-level manual publisher utility.

---

## 5. HTTP API

API starts via `make run` (default `127.0.0.1:8000`; override with `SPEC1_API_HOST`/`SPEC1_API_PORT`).

Auth: `SPEC1_API_KEY` enables a header check (no-op if unset). See `src/spec1_api/auth.py`.

### 5.1 Route map (41 routes across 17 routers)

| Router | Routes |
|--------|--------|
| `health` | `GET /health` |
| `metrics` | `GET /metrics` (Prometheus), `GET /metrics/json` |
| `cycle` | `POST /cycle/run`, `GET /cycle/status` |
| `signals` | `GET /signals`, `POST /signals/ingest` |
| `ingest` | `POST /signal` |
| `intel` | `GET /intel` |
| `brief` | `GET /brief`, `GET /brief/history`, `GET /brief/index`, `GET /brief/latest`, `POST /brief/generate`, `GET /brief/{date}` |
| `leads` | `GET /leads`, `POST /leads/generate` |
| `psyop` | `GET /psyop`, `POST /psyop/analyse`, `POST /psyop/run` |
| `fara` | `GET /fara` |
| `verdicts` | `POST /verdicts`, `GET /verdicts`, `GET /verdicts/{record_id}` |
| `calibration` | `GET /calibration/report`, `GET /calibration/proposals` |
| `workspace` | `GET /workspace/cases`, `POST /workspace/cases`, `GET /workspace/cases/{case_id}`, `POST /workspace/cases/{case_id}/findings`, `POST /workspace/cases/{case_id}/close` |
| `publication` | `GET /publication/latest`, `GET /publication/list`, `POST /publication/generate`, `GET /publication/{filename}` |
| `adapters` | `GET /adapters`, `GET /adapters/{name}` |
| `nodes` | `GET /nodes/{node_id}/signal` |
| `leg_jud` | `GET /leg_jud/brief`, `GET /leg_jud/brief/history`, `GET /leg_jud/judicial`, `GET /leg_jud/state_leg` |

Path prefixes are set in `src/spec1_api/main.py`. Open the OpenAPI doc at `http://127.0.0.1:8000/docs` when the server is running.

### 5.2 curl examples

```bash
# Health
curl -s http://127.0.0.1:8000/health | jq

# Trigger an intelligence cycle
curl -s -X POST http://127.0.0.1:8000/cycle/run \
     -H 'Content-Type: application/json' \
     -d '{}' | jq

# Score a text for psyop patterns
curl -s -X POST http://127.0.0.1:8000/psyop/analyse \
     -H 'Content-Type: application/json' \
     -d '{"text": "Some narrative text to score"}' | jq

# Latest brief
curl -s http://127.0.0.1:8000/brief/latest | jq

# File a verdict
curl -s -X POST http://127.0.0.1:8000/verdicts \
     -H 'Content-Type: application/json' \
     -d '{"record_id":"rec_abc123","verdict":"correct","reviewer":"matt"}' | jq
```

Deep dive: [`docs/api.md`](api.md).

---

## 6. MCP Server

`mcp_server.py` runs as a JSON-RPC server over stdio. Start with `make mcp` or `python mcp_server.py`.

### 6.1 Tool catalog (15)

| Tool | Required args | Purpose |
|------|---------------|---------|
| `run_cycle` | — | Run a canonical cycle and return the count |
| `get_signals` | — | Return recent OSINT signals (`limit` optional, max 200) |
| `get_intel` | — | Return intel records (`limit`, `min_confidence`) |
| `get_leads` | — | Return Leads (`limit`, `priority`) |
| `get_brief` | — | Return latest world brief |
| `get_psyop` | — | Return stored psyop scores (`limit`, `min_classification`) |
| `get_fara` | — | Return FARA records (`limit`, `country`) |
| `analyse_psyop` | `text` | Score a single text snippet |
| `get_stats` | — | Counts across every store |
| `file_verdict` | `record_id`, `verdict` | Append a human verdict |
| `get_verdicts` | — | Read verdicts (filter by `record_id`) |
| `run_psyop` | — | Re-score every intel record |
| `generate_brief` | — | Generate a brief (Claude Sonnet → rule-based fallback) |
| `generate_leads` | — | Derive Leads from intel |
| `get_calibration` | — | Drift report (`include_proposals`, `sample_floor`, `delta_floor`) |

### 6.2 JSON-RPC example

```bash
# initialize → list tools → call get_stats
{
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}'
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_stats","arguments":{}}}'
} | python mcp_server.py
```

Each line is one JSON-RPC request. Responses are emitted as JSON lines on stdout.

---

## 7. Models

SPEC-1 uses Anthropic models with an optional Ollama fallback.

| Model ID | Subsystem | File | Purpose |
|----------|-----------|------|---------|
| `claude-sonnet-4-6` | Briefing | `src/spec1_core/briefing/generator.py:33` | Daily brief generation |
| `claude-sonnet-4-6` | PDX1 narrative | `src/cls_pdx1/explain/summarize.py:43` | Portland-1 narrative summaries |
| `claude-haiku-4-5-20251001` | Investigation | `src/spec1_core/investigation/verifier.py:19` | Verifier loop (cheap, fast) |
| `claude-haiku-4-5-20251001` | LLM fallback default | `src/spec1_core/llm/fallback_client.py:29` | Default tier-1 model |
| `claude-sonnet-4-20250514` | Workspace | `src/spec1_core/workspace/researcher.py:79` | Interactive case-file research |

**Override knob:** `SPEC1_LLM_CLAUDE_MODEL` — honored by `llm/fallback_client.py` only. The other call sites currently hard-code their model. (See [`docs/ACCESS_AUDIT.md`](ACCESS_AUDIT.md) finding F-2 for context.)

**Fallback chain (only in `llm/fallback_client.py`):**

```
ANTHROPIC_API_KEY set?  ─yes──► Anthropic (model = SPEC1_LLM_CLAUDE_MODEL or default)
                        ─no──┐
                             ▼
                  OLLAMA_AUTO_SPAWN ≠ "false" ─yes──► spawn local Ollama → tier 2
                                              ─no──► RuntimeError
```

When Anthropic is unreachable but the call goes through `briefing/generator.py` (not the fallback client), the brief degrades to its rule-based template instead.

---

## 8. Environment Variables

### 8.1 Required for full operation

| Name | Default | Consumer | Purpose |
|------|---------|----------|---------|
| `ANTHROPIC_API_KEY` | — | `briefing`, `verifier`, `fallback_client`, `workspace/researcher`, `cls_pdx1/explain/summarize` | Anthropic auth |

### 8.2 Optional external APIs

| Name | Default | Consumer | Purpose |
|------|---------|----------|---------|
| `QUIVER_API_KEY` | — | `spec1_core.congressional.collector` | Quiver Quantitative for congressional trades |
| `LEGISCAN_API_KEY` | — | `spec1_api.routers.leg_jud` | LegiScan state legislative data |
| `OPENSTATES_API_KEY` | — | `spec1_api.routers.leg_jud` | OpenStates |
| `OLLAMA_AUTO_SPAWN` | `true` | `llm/fallback_client.py` | Auto-spawn Ollama when Anthropic fails |

### 8.3 SPEC1_* configuration

| Name | Default | Consumer | Purpose |
|------|---------|----------|---------|
| `SPEC1_API_HOST` | `127.0.0.1` | `spec1_api.main` | API bind host |
| `SPEC1_API_PORT` | `8000` | `spec1_api.main` | API bind port |
| `SPEC1_API_KEY` | (unset = open) | `spec1_api.auth` | Header-based API key middleware |
| `SPEC1_ENVIRONMENT` | `production` | many | Environment tag in logs/health |
| `SPEC1_CORS_ORIGINS` | (none) | `spec1_api.main` | Comma-separated allowed origins |
| `SPEC1_STORE_PATH` | `spec1_intelligence.jsonl` | many | Primary intel store path |
| `SPEC1_DB_PATH` | (default per cls_db) | `cls_db.database` | SQLite path |
| `SPEC1_VERDICTS_PATH` | `verdicts.jsonl` | verdicts router, cls_verdicts | Verdict store |
| `SPEC1_PSYOP_PATH` | `generated/psyop_scores.jsonl` | psyop router, run_psyop | Psyop store |
| `SPEC1_LEADS_PATH` | `leads.jsonl` | leads router | Lead store |
| `SPEC1_OSINT_PATH` | (per cls_osint) | OSINT routers | OSINT signal store |
| `SPEC1_BRIEFS_DIR` | `briefs` | publication router | Where briefs are written |
| `SPEC1_BRIEFS_PATH` | (per consumer) | other brief lookups | Overlapping with DIR — see ACCESS_AUDIT F-5 |
| `SPEC1_LEG_JUD_PATH` | `leg_jud_briefs.jsonl` | leg_jud router | Legislative/judicial brief store |
| `SPEC1_PUBLISH_LOG` | `publish_log.jsonl` | cls_db.publish_log | Publication audit trail |
| `SPEC1_LLM_CLAUDE_MODEL` | `claude-haiku-4-5-20251001` | `llm/fallback_client.py` | Model override (partial — see F-2) |
| `SPEC1_LLM_LOG_PATH` | (per llm) | llm package | Per-call LLM log |
| `SPEC1_OLLAMA_URL` | (per ollama default) | llm/fallback_client | Ollama endpoint |
| `SPEC1_TIMEZONE` | `America/Los_Angeles` | scheduler | Cron timezone |
| `SPEC1_CRON_HOUR` | `6` | scheduler | Daily cycle hour |
| `SPEC1_CRON_MINUTE` | `0` | scheduler | Daily cycle minute |
| `SPEC1_RUN_ON_START` | (false) | scheduler | Run a cycle at API boot |
| `SPEC1_DEV_MODE` | (false) | various | Dev/test toggles |
| `SPEC1_HEADERS` | (none) | various | Extra HTTP headers for outbound feeds |
| `SPEC1_POLITICAL_WEB_ENABLED` | (false) | spec1_api.main | Enable political-web subsystem |
| `SPEC1_WEBHOOK_URLS` | (none) | webhooks | Comma-separated outbound webhooks |
| `SPEC1_WEBHOOK_SECRET` | (none) | webhooks | HMAC-SHA256 secret |
| `SPEC1_WEBHOOK_TIMEOUT` | `_DEFAULT_TIMEOUT` | webhooks | Per-webhook timeout |

Full inventory: 33 keys total. There is no `.env.example` in the repo today (see ACCESS_AUDIT F-6).

---

## 9. Workflows / Cookbook

### 9.1 Run a one-shot cycle and inspect output

```bash
cd ~/spec-1
export ANTHROPIC_API_KEY=sk-ant-…
make cycle
tail -n 3 spec1_intelligence.jsonl | jq
```

### 9.2 Generate a daily brief

```bash
make brief                            # uses latest run_id by default
ls -t briefs/spec1_brief_*.md | head -1
```

Brief generation tries Claude Sonnet first; falls back to the rule-based template if the API call fails (see [`docs/architecture.md`](architecture.md) briefing section).

### 9.3 Score every record for psyop patterns

```bash
make psyop
head -n 1 generated/psyop_scores.jsonl | jq
```

### 9.4 File a verdict on a record

Via HTTP:
```bash
curl -s -X POST http://127.0.0.1:8000/verdicts \
     -H 'Content-Type: application/json' \
     -d '{"record_id":"rec_abc123","verdict":"correct","reviewer":"matt","notes":"matches independent source"}' | jq
```

Via MCP:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"file_verdict","arguments":{"record_id":"rec_abc123","verdict":"correct","reviewer":"matt"}}}' | python mcp_server.py
```

### 9.5 Produce a calibration drift report

```bash
make calibration
ls -t generated/calibration_*.md | head -1
```

The report is descriptive only — it does **not** auto-tune scorer weights.

### 9.6 Start the API + dashboard

```bash
make run                              # background-friendly: nohup make run > api.log 2>&1 &
open spec1_ui.html                    # or just paste path in a browser
```

The dashboard's header shows `API Online` when reachable.

### 9.7 Boot the MCP server and call a tool

```bash
make mcp &                            # MCP runs on stdio — useful for testing piped
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_stats","arguments":{}}}' \
  | python mcp_server.py
```

In practice the MCP server is launched by Claude Code via its `claude_desktop_config.json` — manual stdio is mostly for tests.

### 9.8 Backfill historical briefs

```bash
make backfill
```

Walks `spec1_intelligence.jsonl`, identifies `run_id`s missing a brief, and generates one for each.

---

## 10. File Layout

```
spec-1/
├── Makefile                          # the operator-facing command surface
├── README.md                         # public landing copy
├── CLAUDE.md                         # agent governance for in-repo work
├── ROADMAP.md                        # 26-week strategic plan (product, not ops)
├── AUDIT_REPORT.md                   # prior commit-hygiene audit (2026-05-20)
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── mcp_server.py                     # MCP JSON-RPC server (stdio)
├── spec1_ui.html                     # static dashboard / workbench
├── spec1_intelligence.jsonl          # CANONICAL intel store (append-only)
├── leads.jsonl                       # operator-tool output
├── psyop_scores.jsonl                # operator-tool output
├── world_briefs.jsonl                # daily brief store
├── pdx1_local.db                     # PDX1 SQLite
├── src/
│   ├── spec1_api/                    # FastAPI app
│   │   ├── main.py                   # entry: python -m spec1_api.main
│   │   ├── auth.py                   # SPEC1_API_KEY middleware
│   │   ├── dependencies.py
│   │   ├── scheduler.py              # cron scheduler
│   │   ├── webhooks.py
│   │   ├── metrics.py                # Prometheus + /metrics/json
│   │   ├── routers/                  # 17 routers
│   │   │   ├── health.py             # GET /health
│   │   │   ├── cycle.py              # POST /cycle/run, GET /cycle/status
│   │   │   ├── signals.py            # GET /signals, POST /signals/ingest
│   │   │   ├── ingest.py             # POST /signal
│   │   │   ├── intel.py              # GET /intel
│   │   │   ├── brief.py              # 6 brief endpoints
│   │   │   ├── leads.py              # GET /leads, POST /leads/generate
│   │   │   ├── psyop.py              # 3 psyop endpoints
│   │   │   ├── fara.py               # GET /fara
│   │   │   ├── verdicts.py           # 3 verdict endpoints
│   │   │   ├── calibration.py        # report + proposals
│   │   │   ├── workspace.py          # 5 case endpoints
│   │   │   ├── publication.py        # 4 publication endpoints
│   │   │   ├── adapters.py           # GET /adapters
│   │   │   ├── nodes.py              # GET /nodes/{id}/signal
│   │   │   ├── leg_jud.py            # 4 leg/jud endpoints
│   │   │   └── metrics.py            # 2 metrics endpoints
│   │   └── schemas/
│   ├── spec1_engine/                 # FROZEN core pipeline
│   │   ├── core/                     # DO NOT EDIT without explicit approval
│   │   ├── signal/                   # harvester, parser, scorer, complexity
│   │   ├── investigation/            # generator, verifier
│   │   ├── intelligence/             # analyzer, store
│   │   ├── analysts/                 # registry, credibility, discovery
│   │   ├── briefing/                 # Claude Sonnet generator + rule fallback
│   │   ├── congressional/            # collector, parser, scorer, analyzer, cycle
│   │   ├── quant/                    # collector, parser, scorer, analyzer, cycle
│   │   ├── workspace/                # persistent case CLI + researcher
│   │   ├── tools/                    # operational python -m CLIs
│   │   ├── app/                      # cycle entrypoint
│   │   └── main.py
│   ├── cls_osint/                    # FARA, congressional, narrative adapters
│   ├── cls_world_brief/
│   ├── cls_leads/
│   ├── cls_psyop/
│   ├── cls_verdicts/
│   ├── cls_calibration/
│   ├── cls_db/                       # SQLite dual-write layer
│   ├── cls_pdx1/                     # Portland regional adapter
│   ├── spec1_core/                   # engine internals + LLM client
│   ├── spec1_analytics/              # read-only analytics
│   └── spec1_labels.py
├── tests/                            # 1000+ pytest cases
├── docs/                             # this directory
│   ├── SHOP_MANUAL.md                # ← you are here
│   ├── ACCESS_AUDIT.md               # companion audit
│   ├── architecture.md
│   ├── api.md
│   ├── runbook.md
│   ├── quickstart.md
│   ├── deployment.md
│   ├── customization.md
│   ├── case_study.md
│   ├── portfolio.md
│   ├── api-integration.md
│   └── scalability_tracker.md
├── scripts/
│   ├── run_cycle.sh
│   ├── setup_dev.sh
│   └── anthropic_smoke.py
├── tools/
│   └── manual_publisher.py
├── briefs/                           # generated brief markdown
├── generated/                        # operator-tool outputs (calibration, psyop)
├── memory/                           # decisions.md, context.md
├── workspace/                        # persistent case files
└── venv/                             # local virtual env (gitignored)
```

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pip install -e ".[dev]"` fails on `sgmllib3k` | Build error on standard pip | Use a fresh venv (`python -m venv venv && source venv/bin/activate`) then re-run, or `pip install sgmllib3k --no-build-isolation` first |
| `ANTHROPIC_API_KEY not set` runtime error | env not exported | `export ANTHROPIC_API_KEY=sk-ant-…` or add to `.env` and source it |
| `make cycle` hangs > 90s | RSS feed slow / network timeout | Let it finish, or set per-source timeouts in `cls_osint/feed.py`; check `SPEC1_HEADERS` if a feed needs auth |
| Brief generation falls back to rule-based template | Anthropic call failed or `ANTHROPIC_API_KEY` missing | Confirm key, then `python scripts/anthropic_smoke.py`; check `SPEC1_LLM_LOG_PATH` |
| API returns 401 | `SPEC1_API_KEY` mismatch | Send the right `X-API-Key` header, or unset `SPEC1_API_KEY` to disable the middleware |
| MCP tool returns `Error: file not found` | Store path env var unset or wrong | Check `SPEC1_STORE_PATH`, `SPEC1_VERDICTS_PATH`, `SPEC1_PSYOP_PATH` |
| Dashboard shows `API Offline` | API server not running | `make run`, then refresh; check `SPEC1_API_HOST`/`SPEC1_API_PORT` if non-default |
| `make calibration` writes no proposals | sample size below `sample_floor` | Lower `--delta-floor`/`--sample-floor` or file more verdicts |
| `python -m spec1_engine.workspace` exits immediately | No cases yet | Create one: `POST /workspace/cases` or use the CLI's `new` command |
| `tweepy` import error in publisher | Optional dep missing | `pip install tweepy` (see ACCESS_AUDIT note — not in pyproject) |
| `weasyprint` import warning in tests | OS package missing | Acceptable — tests skip on missing weasyprint. Install via OS for PDF rendering |
| Ollama tier doesn't fire when Anthropic fails | `OLLAMA_AUTO_SPAWN=false` or ollama not installed | Set `OLLAMA_AUTO_SPAWN=true` and `which ollama` |

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **Signal** | Raw item harvested from a source (RSS entry, FARA filing, congressional trade) |
| **ParsedSignal** | Normalized Signal after `cls_osint` parser stage |
| **Opportunity** | Parsed signal that crossed the 4-gate score threshold and is worth investigating |
| **Investigation** | Claude-generated investigation hypothesis (verifier loop runs against this) |
| **IntelligenceRecord** | Final canonical artifact: verified, scored, append-only entry in `spec1_intelligence.jsonl` |
| **Verdict** | Human ground-truth label on an IntelligenceRecord (`correct`/`incorrect`/`partial`/`unclear`) — Phase 1 feedback loop |
| **Lead** | Operator-actionable item derived from one or more IntelligenceRecords |
| **Brief** | Daily world intelligence markdown report (Claude Sonnet primary, rule-based fallback) |
| **Calibration** | Phase 2 feedback loop: descriptive drift report aggregated from verdicts — **never auto-applies tuning** |
| **Bucket** | Score-band used by calibration aggregator |
| **Psyop classification** | `CLEAN` / `LOW_RISK` / `MEDIUM_RISK` / `HIGH_RISK` |
| **FARA** | Foreign Agents Registration Act — DoJ filings that disclose foreign-principal representation |
| **`run_id`** | Identifier for one cycle execution; ties briefs, leads, and verdicts back to the records produced in that cycle |
| **4-gate pipeline** | The deterministic score gates applied during the cycle: harvest → parse → score → investigate (the four sequential transitions) |
| **Dual-write** | The pattern of appending to JSONL **and** writing to SQLite (`cls_db`) in the same transaction |

---

*Last updated: 2026-05-23.  Maintained alongside `docs/ACCESS_AUDIT.md`. Authoritative for operations; deep-dive architecture and per-domain detail live in their own docs.*

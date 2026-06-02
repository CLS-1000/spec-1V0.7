# SPEC-1 Access & Efficiency Audit

**Date:** 2026-05-23
**Auditor:** PAI / Algorithm v6.3.0 (Opus 4.7), cross-verified at VERIFY by Cato (GPT-5.4).
**Scope:** Command access, tool access, model access, and efficiency findings across the spec-1 program.
**Prior work:** `AUDIT_REPORT.md` (2026-05-20) covered commit hygiene; this audit covers the program's *runtime action surface*.

---

## 1. TL;DR

spec-1 exposes **15 Makefile targets**, **9 `python -m` entry points**, **41 FastAPI routes** across **17 routers**, **15 MCP tools** in `mcp_server.py`, calls **3 distinct Anthropic model IDs**, and reads **33 environment-variable keys** across the codebase.

The workbench UI (`spec1_ui.html`) currently exposes roughly **6 of those ~80 actions** as clickable affordances. The remaining ~75 are reachable only by reading the Makefile, the FastAPI router source, or the MCP server source. **The biggest access gap is in the UI, not in the code.**

The biggest efficiency gap is **scattered model-ID literals**: three different Anthropic model IDs are hard-coded across five files, including one stale model (`claude-sonnet-4-20250514` in `src/spec1_core/workspace/researcher.py`), and only one of the five callers honors the `SPEC1_LLM_CLAUDE_MODEL` override env var.

---

## 2. Method

| Surface | How enumerated |
|---------|----------------|
| Make targets | `cat Makefile`, scan `.PHONY` and rule names |
| `python -m` entry points | `grep -rE 'python -m \S+' Makefile docs/ scripts/` plus `find src -name __main__.py -or -name main.py` |
| FastAPI routes | `grep -rE '@router\.' src/spec1_api/routers/ --include="*.py"` |
| MCP tools | `grep -n 'def tool_' mcp_server.py` cross-checked against `TOOLS` registry dispatch block |
| Model IDs | `grep -rE 'claude-(haiku\|sonnet\|opus)-' src/ --include="*.py"` |
| Env vars | `grep -rohE "os\\.(environ\\.get\|getenv)\\(\\s*['\"]\\w+['\"]" src/ mcp_server.py scripts/ tools/ \| sort -u` |
| UI affordances | `grep -nE '(onclick=\|button\|run-btn\|copy-btn)' spec1_ui.html` |

All grep evidence is reproducible. Where I found mismatches between sources (e.g. CLAUDE.md vs. actual code), I trust the code.

---

## 3. Command surface

### 3.1 Makefile targets (15)

| Target | One-line description | Calls |
|--------|---------------------|-------|
| `install` | Install package + dev deps | `pip install -e ".[dev]"` |
| `test` | Run full pytest suite | `pytest tests/ -v --tb=short` |
| `test-fast` | Stop on first failure | `pytest tests/ -x --tb=short -q` |
| `test-cov` | Coverage report | `pytest tests/ --cov=src --cov-report=term-missing` |
| `lint` | Lint src + tests | `flake8 ... --max-line-length=120` |
| `run` | Start FastAPI server (port 8000) | `python -m spec1_api.main` |
| `mcp` | Start MCP server (stdio) | `python mcp_server.py` |
| `cycle` | One-shot intelligence cycle | `python -m spec1_engine.app.cycle` |
| `backfill` | Backfill historical briefs | `python -m spec1_engine.tools.historical_briefs` |
| `calibration` | Generate calibration proposal | `python -m spec1_engine.tools.calibration_propose ...` |
| `brief` | Generate daily brief | `python -m spec1_engine.tools.generate_brief` |
| `leads` | Derive Leads | `python -m spec1_engine.tools.generate_leads` |
| `psyop` | Score psyop on every record | `python -m spec1_engine.tools.run_psyop` |
| `workspace` | Open workspace CLI | `python -m spec1_engine.workspace` |
| `clean` | Remove __pycache__ + .pytest_cache | shell `find ... -exec rm -rf` |

### 3.2 `python -m` entry points reachable outside Makefile (9 total)

`spec1_api.main`, `spec1_engine.app.cycle`, `spec1_engine.main`, `spec1_engine.tools.historical_briefs`, `spec1_engine.tools.calibration_propose`, `spec1_engine.tools.generate_brief`, `spec1_engine.tools.generate_leads`, `spec1_engine.tools.run_psyop`, `spec1_engine.workspace`.

### 3.3 Shell scripts (3)

`scripts/run_cycle.sh`, `scripts/setup_dev.sh`, `scripts/anthropic_smoke.py`. Plus `tools/manual_publisher.py` (top-level publisher utility).

---

## 4. HTTP API surface

**41 routes** across **17 routers** under `src/spec1_api/routers/`. Mount prefixes are set in `src/spec1_api/main.py` (read alongside this table).

| Router file | Routes |
|-------------|--------|
| `adapters.py` | `GET ""`, `GET "/{name}"` |
| `brief.py` | `GET ""`, `GET "/history"`, `GET "/index"`, `GET "/latest"`, `POST "/generate"`, `GET "/{date}"` |
| `calibration.py` | `GET "/report"`, `GET "/proposals"` |
| `cycle.py` | `POST "/run"`, `GET "/status"` |
| `fara.py` | `GET ""` |
| `health.py` | `GET "/health"` |
| `ingest.py` | `POST "/signal"` |
| `intel.py` | `GET ""` |
| `leads.py` | `GET ""`, `POST "/generate"` |
| `leg_jud.py` | `GET "/brief"`, `GET "/brief/history"`, `GET "/judicial"`, `GET "/state_leg"` |
| `metrics.py` | `GET ""` (Prometheus), `GET "/json"` |
| `nodes.py` | `GET "/{node_id}/signal"` |
| `psyop.py` | `GET ""`, `POST "/analyse"`, `POST "/run"` |
| `publication.py` | `GET "/latest"`, `GET "/list"`, `POST "/generate"`, `GET "/{filename}"` |
| `signals.py` | `GET ""`, `POST "/ingest"` |
| `verdicts.py` | `POST ""`, `GET ""`, `GET "/{record_id}"` |
| `workspace.py` | `GET "/cases"`, `POST "/cases"`, `GET "/cases/{case_id}"`, `POST "/cases/{case_id}/findings"`, `POST "/cases/{case_id}/close"` |

Authentication: `src/spec1_api/auth.py` adds a no-op-if-unset `SPEC1_API_KEY` middleware on every route.

---

## 5. MCP tool surface

15 tools registered in `mcp_server.py`'s `TOOLS` dict and served via JSON-RPC stdio:

| Tool | Required args | Reads from / writes to |
|------|---------------|------------------------|
| `run_cycle` | — | runs canonical cycle (writes `SPEC1_STORE_PATH`) |
| `get_signals` | — | reads OSINT signal store |
| `get_intel` | — | reads `SPEC1_STORE_PATH` |
| `get_leads` | — | reads leads jsonl |
| `get_brief` | — | reads latest brief markdown |
| `get_psyop` | — | reads psyop scores jsonl |
| `get_fara` | — | reads FARA records |
| `analyse_psyop` | `text` | computes psyop score in-process |
| `get_stats` | — | counts across all stores |
| `file_verdict` | `record_id`, `verdict` | appends to `SPEC1_VERDICTS_PATH` |
| `get_verdicts` | — | reads verdicts jsonl |
| `run_psyop` | — | rescores every intel record |
| `generate_brief` | — | calls Claude Sonnet, falls back to rule-based |
| `generate_leads` | — | derives Leads from intel |
| `get_calibration` | — | aggregates verdicts → drift report |

---

## 6. Model access surface

Three distinct Anthropic model IDs are hard-coded across the codebase:

| Model ID | Used in | Purpose | Honors `SPEC1_LLM_CLAUDE_MODEL`? |
|---|---|---|---|
| `claude-sonnet-4-6` | `src/spec1_core/briefing/generator.py:33` | Daily brief generation | NO |
| `claude-sonnet-4-6` | `src/cls_pdx1/explain/summarize.py:43` | PDX1 narrative summary | NO |
| `claude-haiku-4-5-20251001` | `src/spec1_core/investigation/verifier.py:19` | Investigation verifier | NO |
| `claude-haiku-4-5-20251001` | `src/spec1_core/llm/fallback_client.py:29` (default) | LLM fallback tier 1 | **YES** (sole consumer) |
| `claude-sonnet-4-20250514` | `src/spec1_core/workspace/researcher.py:79` | Workspace research agent | NO |

Tier chain (only `llm/fallback_client.py` implements it): Anthropic API → Ollama (`OLLAMA_AUTO_SPAWN`, `SPEC1_OLLAMA_URL`).

Direct `anthropic.Anthropic(api_key=...)` calls occur in: `briefing/generator.py`, `workspace/researcher.py`, `llm/fallback_client.py`, `cls_pdx1/explain/summarize.py`. Only `llm/fallback_client.py` reads `os.environ.get("SPEC1_LLM_CLAUDE_MODEL", ...)`.

---

## 7. Environment-variable surface

33 keys total, grouped by domain.

### 7.1 Secrets / external APIs (5)

`ANTHROPIC_API_KEY`, `QUIVER_API_KEY`, `LEGISCAN_API_KEY`, `OPENSTATES_API_KEY`, `OLLAMA_AUTO_SPAWN`.

### 7.2 `SPEC1_*` configuration (28)

`SPEC1_API_HOST`, `SPEC1_API_KEY`, `SPEC1_API_PORT`, `SPEC1_BRIEFS_DIR`, `SPEC1_BRIEFS_PATH`, `SPEC1_CORS_ORIGINS`, `SPEC1_CRON_HOUR`, `SPEC1_CRON_MINUTE`, `SPEC1_DB_PATH`, `SPEC1_DEV_MODE`, `SPEC1_ENVIRONMENT`, `SPEC1_HEADERS`, `SPEC1_LEADS_PATH`, `SPEC1_LEG_JUD_PATH`, `SPEC1_LLM_CLAUDE_MODEL`, `SPEC1_LLM_LOG_PATH`, `SPEC1_OLLAMA_URL`, `SPEC1_OSINT_PATH`, `SPEC1_POLITICAL_WEB_ENABLED`, `SPEC1_PSYOP_PATH`, `SPEC1_PUBLISH_LOG`, `SPEC1_RUN_ON_START`, `SPEC1_STORE_PATH`, `SPEC1_TIMEZONE`, `SPEC1_VERDICTS_PATH`, `SPEC1_WEBHOOK_SECRET`, `SPEC1_WEBHOOK_TIMEOUT`, `SPEC1_WEBHOOK_URLS`.

---

## 8. UI affordance surface

`spec1_ui.html` (1319 lines) currently surfaces these clickable actions to operators:

| Action | UI mechanism | Backing endpoint |
|--------|--------------|------------------|
| Run intelligence cycle | `▷ Run Intelligence Cycle` button | `POST /cycle/run` |
| Analyse text for psyop | `Analyse for Psyop Patterns` button | `POST /psyop/analyse` |
| Submit verdict | `Submit Verdict` button | `POST /verdicts` |
| Filter / browse panels | per-domain filter inputs | various `GET` endpoints |
| Local-access copy commands | 5 `copy-btn` blocks | shell commands |
| Start API hint | start-overlay | shell only |

Roughly **6 distinct executable actions** out of ~80 are surfaced. The remaining 74 are reachable only via terminal.

---

## 9. Findings

### F-1 — Inconsistent Anthropic model IDs **[HIGH]**

`workspace/researcher.py` uses `claude-sonnet-4-20250514` (a dated model identifier) while the rest of the codebase uses `claude-sonnet-4-6`. This is drift — once two Sonnet model strings exist, a future model bump will likely miss one. Three Claude model IDs are scattered across five string-literal sites with no central registry.

**Where:** `src/spec1_core/workspace/researcher.py:79`, `src/spec1_core/briefing/generator.py:33`, `src/cls_pdx1/explain/summarize.py:43`, `src/spec1_core/investigation/verifier.py:19`, `src/spec1_core/llm/fallback_client.py:29`.

**Suggested follow-on (NOT done in this audit):** define `MODEL = os.environ.get("SPEC1_LLM_CLAUDE_MODEL", "claude-sonnet-4-6")` once, import from a central `spec1_core.llm.models` module.

### F-2 — `SPEC1_LLM_CLAUDE_MODEL` override is partial **[MED]**

The env var exists in `llm/fallback_client.py` only. Four other Anthropic call sites ignore it. An operator who sets it expecting a model swap will not get the swap on briefs, investigation, workspace research, or PDX1 summarization.

### F-3 — Briefing and PDX1 bypass the LLM fallback chain **[MED]**

`briefing/generator.py` and `cls_pdx1/explain/summarize.py` instantiate `anthropic.Anthropic(...)` directly and have no Ollama fallback. `llm/fallback_client.py` implements the documented tier-1 → tier-2 fallback but is only used in a subset of LLM paths. When Anthropic is down or rate-limited, briefs degrade to the rule-based fallback (acceptable) and PDX1 just fails.

### F-4 — Workbench exposes ~7% of the action surface **[MED]**

`make help` lists 15 targets; the UI Local Access tab shows 5 copy-commands. 41 API routes exist; the UI invokes ~6. 15 MCP tools exist; the UI invokes 0 (MCP is reachable only from a Claude session). An operator who only opens the dashboard cannot discover `make backfill`, `make calibration`, `make psyop`, `POST /publication/generate`, the full `workspace/*` endpoints, or any MCP tool.

### F-5 — `SPEC1_BRIEFS_DIR` and `SPEC1_BRIEFS_PATH` both exist **[LOW]**

Two env vars cover overlapping concepts: `SPEC1_BRIEFS_DIR` (publication router) and `SPEC1_BRIEFS_PATH` (other paths). Either pick one or document the distinction explicitly. Currently undocumented.

### F-6 — 33 env vars, no `.env.example` **[LOW]**

The env-var surface is wide and not centrally documented. There is no `.env.example` template in the repo (verified by `ls -a ~/spec-1 | grep env`).

### F-7 — `python -m` discoverability is poor **[LOW]**

Each tool is its own `python -m spec1_engine.tools.<name>` entry. There is no unified CLI (e.g. `spec1 <subcommand>`) — operators must read the Makefile to find them. Each tool also has its own arg parsing, so help text is inconsistent.

### F-8 — Stale references in CLAUDE.md (carried over from prior audit) **[MED]**

Prior `AUDIT_REPORT.md` flagged stale `cls_quant` references in `memory/context.md` and `CLAUDE.md`. Not re-checked here; deferred to follow-on.

### F-9 — No live model-cost or model-call telemetry surfaced to UI **[LOW]**

LLM calls are logged to `SPEC1_LLM_LOG_PATH` but the UI does not surface "last brief used model X, latency Y, fallback fired Z." This is a UI gap, not a code gap.

### F-10 — MCP tool list is invisible to the UI **[MED]**

The MCP server runs on stdio; the dashboard cannot call it directly. There is no `GET /mcp/tools` mirror endpoint. An operator running the dashboard is unaware of which tools Claude can invoke through MCP. The workbench rework in this audit publishes the tool catalog in the UI as documentation (the buttons copy a JSON-RPC payload to clipboard for terminal execution).

---

## 10. Out of Scope (anti-scope)

This audit deliberately did **NOT**:

- Refactor any of the files named in F-1..F-3. Findings are descriptive; fixes are follow-on tasks.
- Modify the frozen core (`src/spec1_engine/core/`).
- Touch ROADMAP.md, business strategy, or repo-split decisions.
- Re-run the 2026-05-20 commit-hygiene audit.
- Add new dependencies, new test fixtures, or new Python modules.
- Rewrite existing docs in place (`README.md`, `CLAUDE.md`, `docs/architecture.md`, `docs/api.md`, `docs/runbook.md` are untouched).

## 11. Companion artifacts (this delivery)

- **Workbench rework** — `spec1_ui.html` Workbench panel surfaces every Make target + every MCP tool + key API endpoints as either Run buttons (where HTTP-reachable) or labeled copy-commands.
- **Shop manual** — `docs/SHOP_MANUAL.md` is the single operator entry point for all of the above.

---

## 12. Followup tickets to file (suggested)

1. Central `spec1_core.llm.models` module with one Anthropic model constant per role; remove the five literal model IDs from across the tree.
2. Audit every Anthropic call site to honor `SPEC1_LLM_CLAUDE_MODEL`, or document an explicit "model is hard-coded for this path" decision per file.
3. Route `briefing/generator.py` and `cls_pdx1/explain/summarize.py` through `llm/fallback_client.py` so Ollama is available when Anthropic fails.
4. Add `.env.example` covering all 33 env vars with safe defaults.
5. Decide between `SPEC1_BRIEFS_DIR` and `SPEC1_BRIEFS_PATH`; deprecate the loser.
6. Add `GET /mcp/tools` (or static `mcp_tools.json`) to make the MCP catalog discoverable from the dashboard.
7. Add a tiny `spec1` CLI (click or argparse) that fans out to the `python -m` entry points for discoverability — `spec1 cycle`, `spec1 brief`, `spec1 leads`, etc.

---

*Last updated: 2026-05-23.*

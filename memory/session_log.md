# Session Log

Running log of significant changes, decisions, and findings per work session.
Most recent entry at the top. Keep entries concise — link to PRs or ADRs for detail.

---

## 2026-05-06 — Repo Reorganization

**Branch:** `claude/build-spec1-pipeline-Z3WkU`

**What changed:**
- Added `CHANGELOG.md` at root (full version history v0.1.0 → v0.4.0)
- Created `docs/` folder: `architecture.md`, `api.md`, `runbook.md`
- Moved `CASE_STUDY.md` → `docs/case_study.md`
- Moved `PORTFOLIO_SUMMARY.md` → `docs/portfolio.md`
- Created `memory/` folder: `decisions.md` (7 ADRs), `context.md`, `session_log.md`
- Created `Makefile` with standard dev commands
- Created `scripts/setup_dev.sh` and `scripts/run_cycle.sh`
- Updated `.gitignore` to cover loose runtime artifacts at root
- Updated `README.md` to reference new structure

**Audit finding (from repo-vs-summary check):**
- 10 RSS feeds (not ~6 as documented) — DPRK/Korea layer added in v0.4.0
- 30 test files / 917 tests (not 27 / ~780 as in CLAUDE.md) — codebase grew past docs

**No source code changed.** Tests, schemas, and pipeline untouched.

---

## 2026-05-05 — Portfolio Site + UI

**PRs:** #33 (portfolio site), #37 (spec site)

- `spec1_portfolio.html` — audited portfolio content served statically
- `spec1_ui.html` — default UI at `GET /` with offline brief fallback
- `spec1_api.static` serving both HTML files
- `test_ui_route.py` added

---

## 2026-05-03 — DPRK Fuel Intelligence Layer

**PR:** merged to main

- Added 38 North, NK News, CSIS Korea, Yonhap to `DEFAULT_FEEDS`
- Portland Political Web signal loop with node tooltip API
- Updated feed count assertion in tests

---

## 2026-04-29 — WORLD STATE BRIEF Design

**PR:** #26

- Replaced sacred-geometry PDF template with WORLD STATE BRIEF briefing design
- Updated `user_prompt_template.md` for new psyop evidence-chain keys

---

## 2026-04-28 — Feedback Loop (Verdicts + Calibration)

**PRs:** #25, #26, #28

- `cls_verdicts` — append-only human ground-truth store
- `cls_calibration` — drift surfacing (aggregator, proposer, formatter)
- Calibration is descriptive only — see ADR-005
- API routers: `/verdicts`, `/calibration`
- MCP tools: `file_verdict`, `get_verdicts`, `get_calibration`

---

## 2026-05-02 — WorldStateBrief Schemas + X Publisher

**PRs:** #29, #30

- `WorldStateBrief` value objects
- X (Twitter) publisher integration
- Brief schemas test file added

---

## Template for new entries

```
## YYYY-MM-DD — Short description

**Branch/PR:** ...

**What changed:**
- ...

**Why:**
- ...

**Anything blocked or deferred:**
- ...
```

# [ SPEC-1 INTELLIGENCE ENGINE ]

[![CI](https://github.com/mjlak1000/spec-1/actions/workflows/python-package.yml/badge.svg)](https://github.com/mjlak1000/spec-1/actions/workflows/python-package.yml)
[![Pages](https://github.com/mjlak1000/spec-1/actions/workflows/pages.yml/badge.svg)](https://mjlak1000.github.io/spec-1/)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

```
INIT PID 1...
PYTHON 3.11+ DETECTED
LOADING 1,359 TESTS... [OK]
PIPELINE STATUS: READY
```

Automated OSINT signal triage and geopolitical intelligence synthesis via deterministic 7-stage pipeline.
`// v0.6.0 · Portland OR · EVASTARARCANA`

**Landing:** [mjlak1000.github.io/spec-1](https://mjlak1000.github.io/spec-1/) · **Dashboard:** [/ui](https://mjlak1000.github.io/spec-1/ui/)

---

## Core Problem

Manual triage of 1000+ daily signals across RSS, FARA, Congressional, and narrative sources requires analyst hours. The bottleneck isn't access—it's attention. SPEC-1 replaces manual reading with automated scoring, deduplication, and structured briefs. The system handles volume. You handle judgment.

```
>> SYSTEM DESIGN PRINCIPLE
* Analyst Impact:  Shift from reading to decision-making. Filtered signal replaces
                   raw feed noise. Verdicts feed calibration drift detection.
* Programmer Impact: Graceful degradation. A failed RSS feed does not halt the
                    06:00 AM cron. Dual-write JSONL + SQLite. Source of truth is append-only.
```

---

## Architecture

Seven stages process signals into intelligence records. Each stage fails independently.

```
[01 HARVEST] ──→ [02 PARSE] ──→ [03 SCORE] ──→ [04 INVESTIGATE]
                                     │
                                     ▼
                              Filtered by 4-Gate
                                   System
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ Drops to /dev/null      │
                        │ (noise discarded)       │
                        └────────────────────────���┘

[05 VERIFY] ──→ [06 ANALYZE] ──→ [07 STORE]
     │
     └──→ SQLite / append-only JSONL
```

| Stage | Operation | Output |
|-------|-----------|--------|
| `[01 HARVEST]` | Fetch RSS/Atom with SSL fallback, malformed XML recovery, timeout handling | `Signal[]` |
| `[02 PARSE]` | BeautifulSoup extraction + NLP heuristics. Zero external model dependencies | `ParsedSignal[]` |
| `[03 SCORE]` | Apply 4-gate filter. Single gate failure drops signal | `Opportunity[]` |
| `[04 INVESTIGATE]` | Claude API: hypothesis generation + lead extraction | `Investigation[]` |
| `[05 VERIFY]` | Evidence tree classification | `Outcome[]` |
| `[06 ANALYZE]` | Confidence synthesis from sources and corroboration | `IntelligenceRecord[]` |
| `[07 STORE]` | Dual-write: append-only JSONL (source of truth) + SQLite index | persisted |

---

## The 4-Gate Scoring System

Any gate failure discards the signal. Thresholds are operational; weights unpublished.

| Gate | Criterion | Default |
|------|-----------|---------|
| `[CREDIBILITY]` | Known source or analyst weight ≥ 0.60 | 0.60 |
| `[VOLUME]` | Minimum word count | 50 words |
| `[VELOCITY]` | Recency threshold | ≤ 48h |
| `[NOVELTY]` | Deduplication hash + keyword domain match | ≥ 1 |

---

## Intelligence Adapters

Specialized pipelines for distinct data types. All feed the canonical 7-stage cycle.

| Adapter | Data Source | Signal → Intelligence |
|---------|-------------|----------------------|
| **[FARA]** | DOJ Foreign Agents Registration Act filings | Cross-reference agent registrations against Congressional activity patterns |
| **[CONGRESSIONAL]** | Bills, hearings, disclosures | Trade intelligence via QuiverQuant → Capitol Trades → House eFD fallback chain. Flags defense/cyber/energy sector conflicts |
| **[NARRATIVE]** | Discourse analysis + text clustering | Detect influence operations and astroturfing via TF-IDF cosine similarity. Output: Anomaly + Campaign records |

All adapters write to shared `[ cls_db ]` append-only store.

---

## Deployment Modes

| Mode | Startup | Use Case |
|------|---------|----------|
| **CLI** | `make cycle` | Single-shot analysis, CI/CD integration, ad-hoc signal ingestion |
| **API** | `make run` → `http://localhost:8000` | Scheduled cron (06:00 AM default), webhook-driven manual cycle triggers, dashboard queries |
| **MCP** | `make mcp` | Claude Desktop/IDE agent-driven investigation with full context |
| **Workspace** | `make workspace` | Case management: persistent verdict filing, analyst-driven lead triage |

---

## Modules

**Pipeline**
- `[ spec1_core ]` — 7-stage cycle. Frozen state; changes require version bump + approval
- `[ cls_osint ]` — RSS/FARA/Congressional/Narrative adapters + feed registry
- `[ spec1_api ]` — FastAPI service, APScheduler cron, dual-write persistence, MCP surface

**Intelligence Products**
- `[ cls_world_brief ]` — Daily brief via Claude Sonnet or rule-based fallback
- `[ cls_leads ]` — Extracted leads with confidence scores and analyst assignments
- `[ cls_psyop ]` — Narrative anomaly detection and campaign scoring
- `[ cls_pdx1 ]` — Portland metro-specific briefing (officials, entities, districts)
- `[ cls_quant ]` — Defense/cyber/energy/macro equity watchlist monitoring via yfinance
- `[ cls_db ]` — Dual-write JSONL + SQLite persistence layer

**Feedback Loop**
- `[ cls_verdicts ]` — Append-only human ground-truth verdict collection
- `[ cls_calibration ]` — Drift detection + threshold adjustment proposals (human-decided)

---

## Data Sources

**RSS/Atom Feeds**
- War on the Rocks, Cipher Brief, Just Security, RAND, Atlantic Council, Defense One

**FARA**
- DOJ bulk filings, cross-referenced against Congressional activity

**Congressional**
- Bills, hearings, equity disclosures via QuiverQuant → Capitol Trades → House eFD

**Narrative & Regional**
- Influence-operation detection; Oregon OLIS/ORESTAR; Washington PDC

**Equities**
- Defense primes, cybersecurity vendors, energy majors, macro instruments (yfinance)

---

## Quick Start

```bash
bash scripts/setup_dev.sh
# Or manually:
pip install -e ".[dev]"
cp .env.example .env  # set ANTHROPIC_API_KEY
```

```bash
make cycle        # one-shot: harvest → store
make run          # API server on 0.0.0.0:8000
make mcp          # MCP server (Claude integration)
make brief        # generate brief from latest run_id
make leads        # extract leads from current records
make psyop        # score all records for narrative anomalies
make calibration  # drift report + threshold proposals
make workspace    # case management CLI
make test         # full test suite
```

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Claude API key (required for investigation + briefing) |
| `SPEC1_STORE_PATH` | `spec1_intelligence.jsonl` | Append-only intelligence record store |
| `SPEC1_DB_PATH` | `spec1.db` | SQLite query index |
| `SPEC1_API_HOST` | `0.0.0.0` | Bind address |
| `SPEC1_API_PORT` | `8000` | Port |
| `SPEC1_CRON_HOUR` | `6` | Daily cycle hour (24h) |
| `SPEC1_TIMEZONE` | `America/Los_Angeles` | Scheduler timezone |
| `SPEC1_FEED_TIMEOUT` | `15` | Feed fetch timeout (seconds) |
| `SPEC1_RUN_ON_START` | `false` | Execute cycle on API startup |

---

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/cycle/run` | Trigger one cycle immediately |
| GET | `/cycle/status` | Last cycle execution metadata |
| GET | `/signals` | Raw harvested signals |
| POST | `/signals/ingest` | Ingest signal manually |
| GET | `/intel` | Intelligence records (JSONL query) |
| GET | `/leads` | Extracted leads with scores |
| POST | `/leads/generate` | Derive leads from current records |
| GET | `/brief/latest` | Latest world brief |
| GET | `/brief/{date}` | Brief by date or run_id |
| POST | `/brief/generate` | Generate brief for run_id |
| GET | `/brief/history` | All briefs, newest first |
| GET | `/psyop` | Narrative anomalies |
| POST | `/psyop/run` | Score all records for anomalies |
| POST | `/psyop/analyse` | Score arbitrary text |
| GET | `/fara` | FARA filing records |
| GET | `/verdicts` | Analyst verdicts |
| POST | `/verdicts` | File verdict on signal |
| GET | `/calibration/report` | Drift detection report |
| GET | `/calibration/proposals` | Threshold adjustment suggestions |

Conditional routes (when `SPEC1_POLITICAL_WEB_ENABLED=true`):
- `GET /nodes/{node_id}/signal` — Political network node context
- `POST /ingest/signal` — Webhook signal ingestion

---

## Typical Output

**Brief** (`GET /brief/latest`):
```json
{
  "date": "2026-04-12",
  "run_id": "run-20260412-060000",
  "elevated_signals": 3,
  "key_topics": ["Ukraine defense spending", "Taiwan semiconductor vulnerabilities"],
  "lead_count": 12,
  "verdicts_filed": 8,
  "summary": "Low activity. All signals scored below confidence threshold..."
}
```

**Lead** (`GET /leads`):
```json
{
  "id": "lead-001",
  "signal_id": "sig-12345",
  "title": "Defense contractor consolidation signals emerging",
  "source": "Defense One RSS",
  "confidence": 0.78,
  "action": "Monitor Q2 earnings calls for headcount announcements",
  "assigned_analyst": null
}
```

---

## Troubleshooting

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `make cycle` hangs | Network timeout or unreachable RSS endpoint | Increase `SPEC1_FEED_TIMEOUT` or verify endpoint connectivity |
| Brief generation fails | Invalid `ANTHROPIC_API_KEY` or API quota exhausted | Verify key; check Claude API rate limits and balance |
| SQLite locked | Concurrent writes or stale process | Restart API; check for orphaned processes |
| No signals scored through gates | Thresholds miscalibrated (too strict) | Review `GET /calibration/proposals`; adjust gate weights |
| Duplicate signals persist | Novelty gate not catching hash collisions | File verdicts to recalibrate; inspect NOVELTY threshold |

---

## Contributing

**Bug Reports**
- File GitHub issue with reproducible steps, logs, and stack trace

**New Data Sources**
- Add feed to `cls_osint/sources.py`; register in feed registry
- Implement adapter if specialized logic required

**Gate Tuning**
- File verdicts on signals; system detects drift via `[ cls_calibration ]`
- Propose threshold changes with supporting evidence

**Development**
- See [CLAUDE.md](CLAUDE.md) for architecture decisions and governance
- Run `make test` before PR submission

---

## Reference

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | System design, data models, failure modes |
| [docs/api.md](docs/api.md) | HTTP API reference and request/response schemas |
| [docs/runbook.md](docs/runbook.md) | Operational procedures and incident response |
| [docs/portfolio.md](docs/portfolio.md) | Stakeholder overview and use cases |
| [docs/case_study.md](docs/case_study.md) | Design decisions and tradeoffs |
| [CHANGELOG.md](CHANGELOG.md) | Version history and breaking changes |
| [memory/decisions.md](memory/decisions.md) | Architecture Decision Records (ADRs) |
| [CLAUDE.md](CLAUDE.md) | Developer governance and agent rules |

# SPEC-1: Automated Intelligence Triage Engine

<<<<<<< HEAD
SPEC-1 is a real-time open-source intelligence (OSINT) engine that harvests RSS feeds from authoritative national security sources, parses and scores signals through a 4-gate pipeline, generates investigations, verifies outcomes, and stores intelligence records to JSONL and (optionally) PostgreSQL.
=======
**Version:** 0.6.2 | **Status:** Production-Ready  
**Organization:** EVASTARARCANA LLC • Portland, OR
>>>>>>> origin/main

---

<<<<<<< HEAD
```
RSS Harvest → Parse → Score (4 gates) → Investigation → Verify → Intelligencepip → JSONL + PostgreSQL Store
```
=======
## The Problem Intelligence Operations Face
>>>>>>> origin/main

Intelligence analysts face a paradox: drowning in data but starving for insight.

Every day, credible reporting flows from dozens of authoritative sources. The signal-to-noise ratio is brutal. By the time an analyst manually triages the week's feeds, actionable intelligence has grown cold. The bottleneck isn't information access. It's human attention.

SPEC-1 solves this differently.

---

## What SPEC-1 Does

SPEC-1 is a production-grade automated intelligence triage engine that ingests 40+ curated open-source feeds and transforms them into verified, analyst-ready briefs through a deterministic, zero-bypass filtration pipeline.

**Result:** Analysts make high-stakes judgments about verified signals, not manually sort noise.

---

## Why SPEC-1 Is Different

### Strict Filtration

SPEC-1 rejects black-box scoring. The pipeline enforces a zero-bypass policy:

**All four gates must pass, or the signal is discarded.**

Each gate is deterministic, fully logged, and defensible:
- **Provenance Gate:** Source credibility baseline (≥0.75 required)
- **Complexity Gate:** Signals must be novel or actionable
- **Recency Gate:** Fresher intelligence outranks stale reporting
- **Anomaly Gate:** Deep semantic validation for narrative inconsistencies

Analysts see exactly why each signal passed. No mystery. No hidden scoring.

### Enterprise Reliability

- **Immutable audit trail:** All intelligence is append-only. Complete provenance.
- **Failure-first design:** Every stage is heavily logged. Pipeline never crashes.
- **Human-in-the-loop:** Thresholds never auto-calibrate. Humans decide.
- **SLA-ready:** 59 tests, 1,300+ assertions. 100% success rate. <100ms API latency.

### Three-Tier LLM Fallback

Semantic verification never blocks:

Tier 1: Claude Haiku (optimized for speed)  
Tier 2: Local Ollama (zero-cost fallback)  
Tier 3: Deterministic rules (always works)

---

## What You Get

**Daily Intelligence Artifacts**
- World State Brief (publication-ready, sourced)
- High-confidence leads (ranked by priority)
- Narrative anomaly reports (campaign detection)
- Drift alerts (threshold deviations)

**Operational Interfaces**
- REST API (15+ endpoints)
- MCP Server (Claude Desktop integration)
- CLI Workspace (case management)
- PDF Export (stakeholder distribution)

**Data Coverage**  
40+ sources: Reuters, AP, Bloomberg, RAND, CSIS, Defense One, Congressional records, FARA filings, regional monitors.

---

## Performance

Harvest cycle: ~30 seconds
Parse throughput: 1,000+ records/minute
Filter latency: <100ms per gate
Brief generation: <5s live / <2s cached
API response: <100ms
Success rate: 100% (never crashes)

---

## Use Cases

**Intelligence Operations**  
Reduce triage time 80%+. Surface verified signals with immutable compliance trails.

**Security Operations**  
Monitor threat feeds, detect narrative anomalies, refine thresholds.

**Geopolitical Risk**  
Track instability signals, correlate events, maintain archives.

**Legal & Compliance**  
Monitor FARA filings with immutable decision records.

---

## Getting Started

Installation:
```bash
<<<<<<< HEAD
 install -e ".[dev]"
python -m spec1_engine.app.cycle
```

## API

The FastAPI service exposes 10 endpoints under `/api/v1`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/cycle/run` | Trigger an immediate pipeline cycle |
| GET | `/cycle/status` | Status of the last completed cycle |
| GET | `/signals/latest` | Most recent harvested signals |
| GET | `/intelligence/latest` | Most recent intelligence records |
| GET | `/brief/latest` | The most recently generated daily brief |
| GET | `/brief/index` | Brief index (all briefs, newest first) |
| GET | `/brief/{date}` | Brief for a specific date (YYYY-MM-DD) |
| POST | `/kill` | Engage the kill switch (halts scheduled cycles) |
| DELETE | `/kill` | Clear the kill switch |

Start the server:

```bash
python -m spec1_engine.main
```

## Persistence

### JSONL (always active)

Records are appended to `spec1_intelligence.jsonl` — an append-only audit trail.

### PostgreSQL (optional)

Set `DATABASE_URL` to activate dual-write to PostgreSQL. The JSONL store remains
the primary audit trail; PostgreSQL enables SQL queries across runs.

```bash
export DATABASE_URL="postgresql://user:password@localhost/spec1"
python -m spec1_engine.app.cycle
```

Install the optional PostgreSQL driver:

```bash
pip install "spec1-engine[postgres]"
```

## Kill Switch

Touch `.cls_kill` in the working directory (or call `POST /api/v1/kill`) to halt
all scheduled cycle runs without stopping the server.

## Running Tests

=======
git clone https://github.com/mjlak1000/spec-1.git
cd spec-1
pip install -e ".[dev]"
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env
```

First Run:
>>>>>>> origin/main
```bash
make cycle                # Complete pipeline
make run                  # API server
make test                 # Test suite
```

See [docs/runbook.md](docs/runbook.md) for production deployment.

---

## Philosophy

SPEC-1 is engineered on one principle: the system does mechanical work; humans make judgments.

Analysts should never waste time in noise. The pipeline is strict, deterministic, and fully auditable because intelligence decisions require accountability. Every signal has been verified multiple times. Every threshold change is human-approved. Every decision is logged.

The system's job: eliminate the 90% of noise so humans focus on the 10% that matters.

---

**SPEC-1** — Automated Intelligence Triage  
Built by EVASTARARCANA in Portland, OR

Designed for humans who make judgments. Engineered for systems that don't.

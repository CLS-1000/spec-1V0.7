# SPEC-1 Intelligence Engine — Portfolio Summary

## What This Is

SPEC-1 is an automated open-source intelligence (OSINT) system built for real-time national security signal monitoring. The canonical cycle harvests, filters, investigates, and analyzes signals from authoritative sources — producing structured intelligence records on a fixed schedule. Downstream artifacts (daily briefs, actionable leads, psyop scores, calibration reports) are explicit operator tools that read from those records, never silent steps inside the cycle.

The system does one thing well: separate signal from noise in a high-volume information environment, and surface what actually matters to a human analyst.

---

## The Problem It Solves

Anyone working in national security, geopolitical risk, or threat intelligence faces the same daily reality: there is far more credible reporting than any human can process. Think tanks, investigative journalists, and defense research organizations produce dozens of new pieces every day. Most are not actionable. A small fraction are.

The challenge is not access to information — it is triage.

SPEC-1 automates that triage. It monitors a curated set of high-credibility sources continuously, evaluates each new signal through a structured scoring framework, and surfaces only those that clear every threshold. Signals that pass are handed to an investigation and verification workflow powered by Claude. The result is a compressed, high-confidence set of intelligence records — ready for human review, without the noise. From those records, an operator chooses what to produce next: a daily brief, prioritized leads, psyop pattern scores, or a calibration report against filed verdicts.

---

## System Architecture

Seven stages. Each transforms the data and gates what moves forward.

```
Harvest → Parse → Score → Investigate → Verify → Analyze → Store
```

A FastAPI service wraps the pipeline for scheduled and on-demand operation. Briefing, leads, psyop scoring, and calibration are operator tools — each reads from the intelligence store on demand, none runs automatically inside the cycle.

### 1. Harvest

The harvester fetches RSS/Atom feeds from a curated list of national security publishers: authoritative think tanks, investigative outlets, and defense policy organizations with consistent editorial standards and domain expertise.

The harvester handles SSL edge cases, malformed XML, and timeout conditions without stopping the cycle. A failed feed is logged and skipped. Output: `Signal` objects carrying source ID, URL, raw text, author, publication timestamp, and engagement metadata.

### 2. Parse

Each signal passes through a parser that strips HTML, extracts clean prose, identifies keywords and named entities, and measures content volume. BeautifulSoup and lightweight NLP heuristics — no external model dependencies.

Output: `ParsedSignal` — normalized text, keyword set, entity set, word count, detected language.

### 3. Score — The Four-Gate Framework

The core filtering layer. Every parsed signal must clear four independent gates to advance. A single failure removes it from further processing.

- **Credibility** — Is this source trustworthy? Each source carries an internal credibility rating reflecting editorial standards, domain expertise, and track record. Low-rated sources do not advance regardless of content.

- **Volume** — Does this signal contain sufficient substance? Thin posts and summaries are filtered out. Only signals with meaningful content depth continue.

- **Velocity** — Is this signal fresh? Intelligence value degrades rapidly. The scoring rewards recency across a sliding time window.

- **Novelty** — Does this signal touch relevant intelligence domains? A keyword evaluation checks for subject matter relevance across a curated domain taxonomy.

Signals clearing all four gates become `Opportunity` objects, each carrying a composite score that blends the four gate dimensions. Opportunities are classified by priority tier based on that score. Threshold constants are documented in the [architecture reference](architecture.md).

### 4. Investigate

Each opportunity is handed to an investigation generator that builds a structured `Investigation` object: a stated hypothesis about what the signal may indicate, research queries targeting authoritative external sources, and analyst leads — domain-relevant subject matter experts drawn from the internal analyst registry.

Analyst selection is domain-aware: signals about Russian military operations surface different leads than signals about cyber operations or energy infrastructure.

### 5. Verify

Each investigation is submitted to Claude (Haiku) for hypothesis evaluation. Claude returns a structured classification with a confidence score:

| Classification | Meaning |
|---------------|---------|
| Corroborated | Evidence supports the hypothesis |
| Escalate | High-confidence, high-urgency finding |
| Investigate | Hypothesis plausible, more research needed |
| Monitor | Signal real but not yet actionable |
| Conflicted | Evidence is contradictory |
| Archive | Does not warrant further attention |

API failures fall through gracefully — the cycle logs the error and continues. No verification failure crashes the pipeline.

### 6. Analyze

The analyzer synthesizes signal, investigation, and verification outcome into a final `IntelligenceRecord`. It blends confidence signals from multiple sources — verification confidence, source credibility, analyst credibility, outcome classification — into a single composite confidence value.

The weighting reflects the relative epistemic weight each source carries. A highly credible source with a corroborated hypothesis from a domain-specialist analyst carries more weight than a mid-tier source with a speculative outcome. The weights are calibrated, not arbitrary.

### 7. Store

Completed `IntelligenceRecord` objects are written to a JSONL file via a thread-safe, append-only store. Records are never overwritten — the store is an immutable log.

---

## Quantitative Signal Domain

Alongside the text-based OSINT pipeline, SPEC-1 monitors a curated watchlist of publicly traded equities across four sectors: defense primes, cybersecurity vendors, energy majors, and macro instruments.

Market signals are processed through their own four-gate framework evaluating watchlist membership, relative volume, daily return magnitude, and deduplication. Signals clearing all four gates enter the same investigation, verification, and analysis pipeline as text signals.

The rationale: defense and cybersecurity equities often move on information that has not yet surfaced publicly in text. Anomalous volume and price action in these names can be an early signal worth investigating.

---

## Daily Intelligence Brief

A briefing operator tool (`make brief`) collects scored intelligence records for a given run and calls Claude Sonnet to produce a structured written brief. It is invoked deliberately after a cycle — never a silent cycle step.

The brief covers executive findings, elevated signals, domain briefings across cyber and geopolitical developments, story leads, and watch list items. Claude writes as a professional intelligence editor: precise, sourced, and without speculation beyond what the evidence supports. Every claim traces back to a scored signal. If the API call fails, a structured rule-based fallback brief is generated from the raw record data — the briefing never returns empty-handed.

---

## Feedback Loop and Calibration

The four-gate framework and composite scoring weights are not fixed arbitrarily. They were developed through iterative exposure to the signal environment — observing what the system surfaced, evaluating whether those signals were actionable, and adjusting thresholds based on that judgment.

### Verdict Collection

`cls_verdicts` captures human ground-truth verdicts on stored intelligence records. Each verdict carries a `kind` — `correct`, `partial`, `incorrect`, or `unclear` — along with reviewer attribution and optional notes. Multiple verdicts per record are allowed; the store is append-only and never overwrites.

### Calibration as Drift Surfacing

`cls_calibration.aggregator` computes a reliability report from filed verdicts: overall accuracy, per-classification accuracy, and reliability buckets across confidence, source weight, and analyst weight dimensions.

`cls_calibration.proposer` surfaces suggested threshold adjustments based on observed drift. These are descriptive proposals — they document what the data suggests. Calibration is a deliberate human decision; the system surfaces what to consider changing and stops there.

This is an explicit design choice. A deterministic scoring system should improve through legible calibration decisions, not silent weight updates. When a threshold is wrong, the failure is diagnosable and the adjustment is a decision someone can argue with, document, and test against the test suite.

### Source Credibility and Analyst Registry

Source credibility ratings and analyst domain weights are not static. As publishers change in quality or focus, their ratings can be updated. As new subject matter experts establish track records, they can be added. This is structured knowledge maintenance — the same process a human analyst undergoes when updating their mental model of which sources and researchers to trust.

### Test Suite as Calibration Anchor

The repo has approximately 825 collected pytest tests across 30 files, covering the engine, OSINT adapters, psyop detection, briefing, persistence, API, MCP server, and operator tools. When a threshold changes during calibration, the tests verify that the change does not silently break intended behavior elsewhere. The test suite is, in a real sense, a changelog of accumulated calibration judgment.

---

## API and Scheduling

A FastAPI application wraps the pipeline for operational use. The API exposes endpoints for triggering a cycle, querying status and statistics, and retrieving signals, records, briefs, leads, verdicts, and calibration reports. The scheduler runs the pipeline on a configurable daily cron cadence. A kill-file mechanism allows operators to pause scheduled execution without modifying configuration.

---

## Recent Expansions

### Legislative & Judicial Desk (`cls_leg_jud`)
A parallel intelligence product tracking legislative activity and judicial proceedings. Monitors bills, hearings, and court actions; scores by relevance to defense, national security, and technology policy; produces a daily desk brief alongside the world brief.

### PDX-1i Metro Citizens Brief (`cls_pdx1`)
A regional intelligence module for Portland's bi-state metro area (Multnomah, Washington, Clackamas OR; Clark WA). Tracks elected officials across 8 jurisdictions, their district assignments, and ties to 17 monitored entities (utilities, universities, transit, law enforcement). Seeds verified data, resolves officials via fuzzy matching, detects anomalies (vacancies, rapid transitions), and publishes findings as structured "Issues" in PDF + markdown + D3 diagrams.

Current focus: Metro Council President vacancy (Lynn Peterson resignation, Duncan Hwang acting president, appointment deadline June 11, 2026).

### Three-Tier LLM Fallback (`spec1_engine.llm`)
An operational resilience pattern: when Claude is unavailable or expensive, fall back to local Ollama, then to rule-based templating. Every major analysis point that calls an LLM is protected by this fallback chain. Prevents service interruptions and enables offline/low-cost operation paths.

### Operations & Publishing
- **Workspace CLI** (`spec1_engine.workspace`) — case management for investigation tracking, analyst notes, verdict filing
- **X/Twitter Publisher** (`spec1_engine.app.publishers.x`) — thread publication with idempotency log, rate-limit aware
- **Publication Export** — PDF (via weasyprint subprocess) and markdown rendering for standalone briefs and analysis docs

---

## Technical Summary

| Dimension | Detail |
|---|---|
| Language | Python 3.9–3.12 |
| Modules | 51 (core engine, 8 intelligence products, 3 persistence/infrastructure) |
| Pipeline stages | 7 (harvest → analyze → store) |
| Test suite | 1,009 tests passing across 37 files |
| Signal sources | RSS (6 publishers), FARA, Congressional records, state political data, narrative/influence ops |
| Scoring framework | 4-gate deterministic filter (credibility, volume, velocity, novelty) |
| AI integration | Claude Haiku (verification, low-cost), Claude Sonnet (briefing, LLM fallback), Ollama (offline), rule-based (always-available) |
| Regional intelligence | PDX-1i metro (57 officials, 40 districts, 17 entities, live OLIS/ORESTAR feeds) |
| Market signals | 4-sector equity watchlist via yfinance |
| Persistence | Append-only JSONL (audit log, source of truth); SQLite dual-write for queries; rebuild-safe |
| Operations | FastAPI HTTP service + APScheduler daily cron + MCP tools for Claude + CLI workspace |
| API | FastAPI + APScheduler |
| Feedback loop | `cls_verdicts` (human verdicts) + `cls_calibration` (drift report, descriptive only) |
| Tests | ~825 collected pytest tests across 30 files |
| Architecture version | v0.4.0 |

---

## Why This Matters

The bottleneck in intelligence work is not information — it is attention. SPEC-1 is designed to protect analyst attention by automating the triage that does not require human judgment: fetching, cleaning, filtering, and structuring. What reaches the analyst is already scored, investigated, verified, and written up.

The human role is what it should be: evaluating findings, directing follow-on research, and making decisions. The system handles the volume. The analyst handles the judgment.

That division of labor is the point.

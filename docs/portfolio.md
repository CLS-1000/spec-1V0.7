# [ SPEC-1 INTELLIGENCE ENGINE ] — Portfolio

`// v0.6.0 · Portland OR · EVASTARARCANA`

---

## What it is

Automated OSINT for national security signal monitoring. SPEC-1 runs a fixed canonical cycle — harvest, filter, investigate, analyze — and produces structured `IntelligenceRecord` objects on a daily schedule. Downstream products (briefs, leads, psyop scores, calibration reports) are explicit operator tools that read from those records. None runs silently inside the cycle.

---

## The problem it solves

The bottleneck is attention, not access.

Authoritative national-security reporting is abundant. Think tanks, investigative journalists, and defense-research organizations produce dozens of pieces daily. Most are not actionable. The challenge is triage — separating the signal from the noise before it reaches an analyst.

SPEC-1 automates that triage: monitors a curated set of high-credibility sources, evaluates each incoming signal through a structured scoring framework, and surfaces only those that clear every threshold. Signals that pass are handed to an investigation and verification workflow powered by Claude. The result is a compressed, high-confidence set of records ready for human review — without the noise.

**The system handles the volume. The analyst handles the judgment.**

---

## Architecture

Seven stages — engineered for graceful degradation.

```
[01 HARVEST] > [02 PARSE] > [03 SCORE] > [04 INVESTIGATE] > [05 VERIFY] > [06 ANALYZE] > [07 STORE]
```

```
>> SYSTEM METADATA LOG
* Analyst Impact:  You never see garbled text or raw HTML — only clean,
                   normalized prose. Stage 1 errors are contained.
* Programmer Impact: A dead RSS feed will not halt the 06:00 AM cron job.
                   Seven sequential stages, each independently fault-tolerant.
```

### `[01 HARVEST]`

Fetches RSS/Atom feeds from a curated list of national-security publishers. Handles SSL edge cases, malformed XML, and timeouts without stopping the cycle. Failed feeds are logged and skipped.
Output: `Signal[]` — source ID, URL, raw text, author, timestamp.

### `[02 PARSE]`

Strips HTML, extracts clean prose, identifies keywords and named entities, measures content volume. BeautifulSoup + NLP heuristics — no external model dependencies.
Output: `ParsedSignal[]` — normalized text, keyword set, entity set, word count.

### `[03 SCORE]` — The 4-Gate Framework

Any single failure drops the signal.

| Gate | Criterion | Default |
|------|-----------|---------|
| `[CREDIBILITY]` | Source rating ≥ 0.60 | 0.60 |
| `[VOLUME]` | Word count ≥ 50 | 50 words |
| `[VELOCITY]` | Recency score ≥ 0.0 (≤ 48h) | 48h |
| `[NOVELTY]` | Keyword domain match ≥ 1 | hash dedup |

Thresholds encode accumulated operational judgment. Gate weights remain unpublished.

```
>> SYSTEM METADATA LOG
* Analyst Impact:  Only signals that matter reach you. The filter is explicit,
                   not probabilistic — every threshold decision is legible.
* Programmer Impact: Thresholds are constants. Calibration is a deliberate
                   human decision backed by the verdict log, never a silent update.
```

Signals clearing all four gates become `Opportunity` objects, each carrying a composite score and priority tier.

### `[04 INVESTIGATE]`

Each opportunity is handed to an investigation generator that produces a stated hypothesis, research queries targeting authoritative external sources, and analyst leads drawn from an internal domain-expert registry. Lead selection is domain-aware: Russian military signals surface different analysts than cybersecurity or energy-infrastructure signals.
Output: `Investigation[]`

### `[05 VERIFY]`

Each investigation is submitted to Claude for hypothesis evaluation. Claude classifies outcome against an evidence decision tree:

| Outcome | Meaning |
|---------|---------|
| `[CORROBORATED]` | Evidence supports the hypothesis — escalate |
| `[INVESTIGATE]` | Hypothesis plausible, more research needed |
| `[MONITOR]` | Signal real, not yet actionable |
| `[CONFLICTED]` | Evidence contradictory |
| `[ARCHIVE]` | No further attention warranted |

API failures fall through gracefully. No verification failure crashes the pipeline.

```
>> SYSTEM METADATA LOG
* Programmer Impact: The cycle never crashes on a verification error.
                   Graceful rule-based fallbacks exist for all API timeouts.
```

### `[06 ANALYZE]`

Synthesizes signal, investigation, and verification outcome into a final `IntelligenceRecord`. Blends confidence signals from source credibility, analyst credibility, and outcome classification into a single composite confidence value.
Output: `IntelligenceRecord[]`

### `[07 STORE]`

Dual-write: append-only JSONL (source of truth) + SQLite (queryable index, rebuildable from JSONL). Records are never overwritten.

```
[STORE: JSONL / SQLite]
```

---

## Intelligence adapters

The core pipeline adapts to specialized intelligence domains.

```
┌──────────────────┬────────────────────┬──────────────────────┐
│     [FARA]       │  [CONGRESSIONAL]   │    [NARRATIVE]       │
├──────────────────┼────────────────────┼──────────────────────┤
│ DOJ bulk         │ Trade intelligence.│ PsyOps detection.    │
│ filings.         │ Fallback chain:    │ TF-IDF cosine        │
│                  │ QuiverQuant →      │ similarity           │
│ Cross-references │ Capitol Trades →   │ clustering.          │
│ foreign agent    │ House eFD.         │                      │
│ registrations    │                    │ Detects narrative    │
│ against          │ Flags defense/     │ seeding and          │
│ congressional    │ cyber/energy       │ astroturfing.        │
│ activity.        │ conflicts.         │                      │
│                  │                    │ Outputs Anomaly/     │
│                  │                    │ Campaign records.    │
└──────────────────┴────────────────────┴──────────────────────┘
                            │
                            ▼
               [STORE: JSONL / SQLite]
```

---

## Quantitative signal domain

Market volume often precedes textual intelligence.

SPEC-1 monitors a curated equity watchlist across four sectors: defense primes, cybersecurity vendors, energy majors, and macro instruments. Market signals clear a parallel 4-gate framework (watchlist membership, relative volume, daily return, deduplication) before merging into the core Claude verification pipeline.

The rationale: defense and cybersecurity equities often move on information that has not yet surfaced in text. Anomalous volume and price action in these names can be an early signal worth investigating.

---

## `[ WORLD STATE BRIEF ]`

`// Publication delivers neutral news intel. // Powered by SPEC-1`

A briefing operator tool (`make brief`) collects scored records for a given cycle run and calls Claude Sonnet to produce a structured written brief. It is invoked deliberately — never a silent cycle step.

Claude writes as a professional intelligence editor: precise, sourced, without speculation beyond what the evidence supports. Every claim traces back to a scored `IntelligenceRecord`. If the API call fails, a structured rule-based fallback brief is generated — the briefing never returns empty-handed.

---

## Feedback loop

The four-gate framework is not fixed arbitrarily — it improves through legible calibration decisions.

**`[ cls_verdicts ]`** — Human ground-truth verdict collection. Each verdict carries a `kind` (`correct | partial | incorrect | unclear`), reviewer attribution, and optional notes. Append-only; multiple verdicts per record allowed.

**`[ cls_calibration ]`** — Computes reliability reports from filed verdicts: overall accuracy, per-classification accuracy, and reliability buckets across confidence, source weight, and analyst weight. Surfaces suggested threshold adjustments as descriptive proposals. Calibration is a deliberate human decision — the system surfaces what to consider, and stops there.

This is an explicit design choice. A deterministic scoring system should improve through legible calibration decisions, not silent weight updates. When a threshold is wrong, the failure is diagnosable and the adjustment is a decision someone can argue with, document, and test against the test suite.

---

## `[ cls_pdx1 ]` — PDX-1i Metro Citizens Brief

A regional intelligence module for Portland's bi-state metro area (Multnomah, Washington, Clackamas OR; Clark WA). Tracks elected and appointed officials across 8 jurisdictions, their district assignments, and ties to 17 monitored entities — utilities (PGE, NW Natural, Portland Water Bureau), public agencies (TriMet, PPB, OHSU), and private-sector networks (Schnitzer).

- `EntityResolver` — deterministic name→ID resolution (exact, token-sort, substring; no external NLP)
- `RollingBaseline` — 90-day rolling sigma detector (TIER_1 = 3σ, publish-eligible)
- `TriggerState` — signal-gated publication (weight threshold + TIER_1 auto-trigger + floor cadence)
- `OrestarAdapter`, `OlisAdapter`, `SeiAdapter`, `WaPdcAdapter` — state campaign finance + legislative feeds
- `IssueBuilder` — neutrality-gated assembly; tone gate + attribution gate at every section
- PDF + markdown + D3 force-directed diagram exporter

Current focus: Metro Council President vacancy (Lynn Peterson, appointment deadline June 11, 2026).

---

## Technical summary

| Dimension | Detail |
|-----------|--------|
| Language | Python 3.9–3.12 |
| Pipeline stages | 7 — `[01]` Harvest → `[07]` Store |
| Test suite | 1,359 tests passing across 37+ files |
| Scoring | 4-gate deterministic filter — credibility, volume, velocity, novelty |
| AI integration | Claude Haiku (verification) · Claude Sonnet (briefing) · Ollama (offline fallback) · rule-based (always-available) |
| Regional intelligence | PDX-1i metro — officials, districts, entities, live OLIS/ORESTAR feeds |
| Market signals | 4-sector equity watchlist via yfinance |
| Persistence | Append-only JSONL (source of truth) · SQLite dual-write (queryable index) |
| Operations | FastAPI + APScheduler · MCP tools for Claude · CLI workspace |
| Feedback | `cls_verdicts` (human verdicts) · `cls_calibration` (drift report, descriptive only) |
| Architecture version | v0.6.0 |

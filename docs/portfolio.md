# [ SPEC-1 INTELLIGENCE ENGINE ]

`v0.6.0 · Portland OR · EVASTARARCANA`

---

## What it is

Python OSINT pipeline. Deterministic 7-stage cycle: harvest RSS/FARA/Congressional feeds → filter through 4-gate scorer → investigate with Claude Haiku → verify → analyze → store. Runs daily at 06:00 PT on APScheduler. FastAPI HTTP surface + MCP server for Claude integration.

---

## What it does

**7-stage cycle:**

| Stage | Output |
|-------|--------|
| `HARVEST` | `Signal[]` — SSL fallback, malformed XML recovery, per-feed timeout |
| `PARSE` | `ParsedSignal[]` — BeautifulSoup + NLP heuristics, no external model deps |
| `SCORE` | `Opportunity[]` — 4-gate filter; single gate failure discards |
| `INVESTIGATE` | `Investigation[]` — hypothesis + analyst leads via Claude Haiku |
| `VERIFY` | `Outcome[]` — evidence tree classification |
| `ANALYZE` | `IntelligenceRecord[]` — confidence synthesis from source + analyst weight |
| `STORE` | Dual-write: append-only JSONL (source of truth) + SQLite (queryable index) |

**4-gate filter (all must clear):**

| Gate | Default threshold |
|------|------------------|
| CREDIBILITY | source rating ≥ 0.60 |
| VOLUME | ≥ 50 words |
| VELOCITY | ≤ 48h old |
| NOVELTY | hash dedup + keyword domain match |

Thresholds are constants. `cls_calibration` surfaces drift as descriptive proposals — humans apply changes.

**Adapters:** FARA (DOJ bulk filings cross-referenced against Congressional activity) · Congressional (QuiverQuant → Capitol Trades → House eFD fallback chain) · Narrative (TF-IDF cosine similarity, psyop/astroturfing detection) · Quant (defense/cyber/energy/macro equity watchlist via yfinance)

---

## What comes out

**June 6, 2026 · run-7117e0eb · 531 records**

| Classification | Count |
|---------------|-------|
| INVESTIGATE | 422 |
| ARCHIVE | 87 |
| MONITOR | 20 |
| ESCALATE | 1 |
| CORROBORATED | 1 |

Confidence range: 0.37–0.82 · avg 0.55 · 42 elevated signals  
Top sources this cycle: nk_news (299), war_on_the_rocks (93), atlantic_council (66), cipher_brief (30)

**Brief — June 6, 2026 (executive summary):**

```
North Korea has crossed from arms supplier to active belligerent: 14,000-plus
troops fighting in Ukraine, indigenous missile variants now landing on Ukrainian
soil, and military medics cycling combat knowledge back to Pyongyang in real
time — this is a force-generation loop, not a transactional favor to Moscow.
The structural read is a three-node defense-industrial axis (Pyongyang–Moscow–
Minsk) that is hardening faster than Western counter-pressure is organizing,
while the Sahel and the Baltic flanks simultaneously absorb attention and
resources. In the next 48 hours watch Seoul's four-way talks proposal and the
Putin-Lukashenko trilateral framing for signal on whether diplomatic off-ramps
are being built or papered over.
```

Additional outputs per cycle: story leads with analyst feed prompts · psyop pattern scores · FARA cross-reference records · calibration drift report

---

## Who uses it

Analysts who need scored, investigated signal instead of raw feed volume. The system handles triage. The analyst handles routing and judgment.

MCP surface (Claude Desktop / IDE): `run_cycle` `get_signals` `get_intel` `get_leads` `get_brief` `get_psyop` `get_fara` `file_verdict` `get_calibration`

Test suite: 1,359 tests · 37 files · `pytest tests/ -v`

---

## Contact

lakampmatt@gmail.com · [github.com/mjlak1000](https://github.com/mjlak1000) · [github.com/sponsors/mjlak1000](https://github.com/sponsors/mjlak1000)

---

`UNCLASSIFIED // OPEN SOURCE // SPEC-1 v0.6.0 // 2026-06-06`

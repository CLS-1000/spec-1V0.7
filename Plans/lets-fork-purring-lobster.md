# Context

spec-1 is the engine. World State Brief is the first product. congress-brief is the
second product — a repo fork of spec-1 that adds federal legislative intelligence
as a domain module, modeled directly on the existing cls_pdx1 (Portland model).

The Portland model (cls_pdx1) is the architectural blueprint:
- officials_seed.json + entities_seed.json — persistent registry of named actors
- sources/ — jurisdiction-specific data adapters (OLIS, ORESTAR, SEI, WA_PDC)
- watch/ — entity watchers for key institutions
- legislation/bills.py — bill tracking
- anomaly.py + gates.py + triggers.py — signal scoring and friction detection
- publication/ — newsletter/brief builder
- neutrality/ — attribution, tone, section neutrality checks

congress-brief follows the same pattern at the federal level.

---

## Fork Target

`/home/mjlak/congress-brief` — full copy of spec-1 repo, new git history

---

## What Gets Added: cls_congress/

Mirrors cls_pdx1 structure, federal scope:

```
src/cls_congress/
  __init__.py
  models.py              — Member, Entity, Affiliation, Signal, Anomaly, Issue
                           (federal equivalents of cls_pdx1 schema)
  pipeline.py            — orchestrates collection → scoring → brief
  anomaly.py             — cross-pillar friction detector
  gates.py               — 4-gate thresholds for federal signals
  triggers.py            — anomaly trigger rules (donation→vote, lobby→bill, etc.)
  resolver.py            — entity resolution (member aliases, PAC→donor linkage)
  sources/
    fec.py               — FEC bulk data / API (campaign finance) ← ORESTAR equivalent
    congress_gov.py      — Congress.gov API (bills, votes, hearings) ← OLIS equivalent
    lda.py               — LDA lobbying disclosures
    senate_sei.py        — Senate financial disclosures ← SEI equivalent
  watch/                 — key entity watchers (major PACs, lobbying firms, industries)
    pacs.py
    lobbying_firms.py
    industries.py
  legislation/
    bills.py             — bill tracking + stated-purpose extraction
  publication/
    builder.py           — brief builder
    newsletter.py        — newsletter formatter
  neutrality/
    attribution.py
    tone.py
    section.py
  data/
    officials_seed.json  — seeded Congress members (name, chamber, state, district,
                           committees, party, term_start)
    entities_seed.json   — PACs, lobbying firms, key industries
    x_handles.json       — Twitter/X handles for members and entities
```

---

## Four Pillars → Module Mapping

| Pillar | cls_congress module | Federal source |
|--------|---------------------|----------------|
| Lobby | sources/lda.py + resolver.py | LDA filings, FARA (already in cls_osint) |
| Campaign | sources/fec.py | FEC bulk/API |
| Member | models.py MemberRegistry + officials_seed.json | Congress.gov, Senate SEI |
| Policy | legislation/bills.py + cls_leg_jud | Congress.gov bills/votes |

Anomaly detection (anomaly.py + gates.py + triggers.py) runs across all four:
- Donation → vote alignment (campaign + policy)
- Lobby contact → committee assignment overlap (lobby + member)
- Financial disclosure gap (member + policy)
- Stated purpose vs observed beneficiary (policy — already in cls_leg_jud)

---

## Phase 2 — Full Implementation Structure

Phase 2 ports cls_pdx1's proven algorithms to the federal scope and builds the four
source adapters. Each component ships with tests (co-committed, not after).

### Core algorithms to port from cls_pdx1 (generic — no PDX-specific logic)

| cls_pdx1 source | congress-brief target | What it does |
|---|---|---|
| `anomaly.py` RollingBaseline | `cls_congress/anomaly.py` | 90-day rolling σ detector |
| `resolver.py` EntityResolver | `cls_congress/resolver.py` | 3-tier deterministic name matching |
| `legislation/bills.py` BillTracker | `cls_congress/legislation/bills.py` | Bill state machine + Signal emission |
| `triggers.py` TriggerPolicy | `cls_congress/triggers.py` | Weight/spacing/floor-cadence publication trigger |
| `publication/builder.py` IssueBuilder | `cls_congress/publication/builder.py` | Neutrality-gated section accumulator |
| `publication/diagram.py` | `cls_congress/publication/diagram.py` | D3 force-directed affiliation graph |
| `publication/newsletter.py` | `cls_congress/publication/newsletter.py` | Markdown + PDF renderer |

### Federal-specific implementations (new)

**`cls_congress/sources/fec.py`** — FEC campaign finance (ORESTAR equivalent)
- Fetch priority: FEC API (`/v1/schedules/schedule_a/`) → FEC bulk CSV → synthetic sample
- Row → Affiliation(edge_type=DONATION, confidence=HARD_RECORD)
- Amount parsing, contributor → entity resolution via EntityResolver

**`cls_congress/sources/congress_gov.py`** — Congress.gov (OLIS equivalent)
- Delegates to spec-1's `cls_osint.adapters.congressional.collect()`
- Converts `CongressRecord` → `Bill` + `Signal`
- Status mapping: INTRODUCED / PASSED_HOUSE / PASSED_SENATE / ENACTED / FAILED

**`cls_congress/sources/lda.py`** — LDA lobbying (FARA equivalent)
- Wraps spec-1's `cls_osint.adapters.fara.collect()` for foreign agents
- Adds domestic lobbying via Senate LDA disclosure API
- Row → Affiliation(edge_type=LOBBYING)

**`cls_congress/sources/senate_sei.py`** — Senate financial disclosures (SEI equivalent)
- Fetch from Senate.gov disclosure repository
- Member → financial interests → Affiliation(edge_type=EMPLOYMENT or BOARD_SEAT)

**`cls_congress/watch/pacs.py`** — Watch top 20 PACs by contribution volume
**`cls_congress/watch/lobbying_firms.py`** — Watch top 10 lobbying firms by LDA spend

**`cls_congress/models.py`** — Add MemberRegistry class (load officials_seed.json, query by name/chamber/state using EntityResolver pattern)

**`cls_congress/pipeline.py`** — Wire all adapters + watch modules + trigger + builder

**`spec1_api/routers/congress_brief.py`** (in congress-brief fork):
- `GET /congress_brief/brief` — latest Issue
- `GET /congress_brief/member/{member_id}` — Member profile + affiliated signals
- `GET /congress_brief/entity/{entity_id}` — Entity profile + affiliated signals
- `GET /congress_brief/anomalies` — Detected anomalies (tier filter)
- `POST /congress_brief/cycle` — Trigger a collection cycle

### Test structure (co-committed with each component)

```
tests/test_congress_models.py       — MemberRegistry load/query, deterministic IDs
tests/test_congress_anomaly.py      — RollingBaseline: sigma calc, edge cases (silent entity, uniform spike)
tests/test_congress_resolver.py     — 3-tier matching: exact, token-sort, substring
tests/test_congress_bills.py        — BillTracker state machine, Signal emission weights
tests/test_congress_triggers.py     — TriggerPolicy: TIER_1 auto, weight threshold, floor cadence
tests/test_congress_sources.py      — FEC/congress_gov/LDA adapters: network fail → synthetic fallback
tests/test_congress_pipeline.py     — run_congress_cycle(): zero signals → no issue; signals → issue generated
tests/test_congress_api.py          — GET /congress_brief/brief 200; GET /anomalies 200
```

### Delivery order (each step: implement + tests, commit)

1. Port `RollingBaseline` + `EntityResolver` → `anomaly.py`, `resolver.py` + tests
2. Port `BillTracker` state machine → `legislation/bills.py` + tests
3. Port `TriggerPolicy` → `triggers.py` + tests
4. Implement `MemberRegistry` in `models.py` + tests
5. Implement `sources/fec.py` (FEC adapter + synthetic fallback) + tests
6. Implement `sources/congress_gov.py` (wraps cls_osint) + `sources/lda.py` + tests
7. Implement `watch/pacs.py` + `watch/lobbying_firms.py`
8. Wire `pipeline.py` end-to-end + tests
9. Port `IssueBuilder` + `newsletter.py` + `diagram.py` → `publication/` + tests
10. Add `spec1_api/routers/congress_brief.py` API routes + tests

---

## Fork Steps

1. `rsync -av --exclude='.git' --exclude='*.db' --exclude='*.jsonl'
   --exclude='venv/' --exclude='__pycache__/' --exclude='*.egg-info'
   --exclude='briefs/' --exclude='generated/' --exclude='logs/'
   --exclude='output/' --exclude='memory/' --exclude='workspace/'
   --exclude='cache/' --exclude='analyst_loop/' --exclude='PSYCHE-OPS/'
   /home/mjlak/spec-1/ /home/mjlak/congress-brief/`

2. `cd /home/mjlak/congress-brief && git init && git add . &&
   git commit -m "chore: fork from spec-1 v0.6.0"`

3. Update pyproject.toml: name=`congress-brief`, version=`0.1.0`

4. Create `src/cls_congress/` scaffold (all files listed above — stubs with
   docstrings and correct imports; no pass-only stubs per CLAUDE.md rule 1)

5. Seed `src/cls_congress/data/officials_seed.json` with current 535 Congress
   members (name, chamber, state, district, committees, party, term_start).
   Start with a representative sample of ~20 covering key committees
   (Finance, Armed Services, Intelligence, Judiciary, Foreign Relations).

6. Wire cls_congress into the existing spec-1 pipeline:
   - Add `cls_congress` to spec1_api/main.py router list
   - Add collection step in cls_osint/pipeline.py (or standalone cycle)

7. `git add . && git commit -m "feat: cls_congress scaffold — federal legislative
   intelligence module (Lobby/Campaign/Member/Policy pillars)"`

---

## Verification

```bash
cd /home/mjlak/congress-brief
PYTHONPATH=src python -c "from cls_congress.pipeline import run; print('OK')"
PYTHONPATH=src python -m pytest tests/test_leg_jud.py -q   # must still pass
```

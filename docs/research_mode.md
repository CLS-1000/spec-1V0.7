# Research Mode

Research Mode is the analyst-defined-topic counterpart to SPEC-1's daily
Signal Mode cycle. Signal Mode answers **"what matters today"** across all
sources; Research Mode answers **"what do I know about this topic, over
time"** for one topic an analyst has explicitly defined.

It is implemented in `src/cls_research/`, with an operator CLI at
`src/spec1_core/tools/run_research.py`.

---

## Signal Mode vs. Research Mode

| | Signal Mode | Research Mode |
|---|---|---|
| Question | What's worth surfacing *today*? | What do I know about *this topic*? |
| Trigger | Scheduled cycle, all sources | Analyst opens a `TopicProfile` |
| Filtering | 4-gate (credibility/volume/velocity/novelty) | Time horizon + exclusions only |
| Output | Daily brief, leads, psyop scores | A versioned, accumulating dossier |
| Lifespan | One cycle, then archived | Persists and grows across runs |
| LLM use | Claude Sonnet w/ rule-based fallback | None — fully deterministic |

Both share the same harvester and parser (`spec1_core.signal.harvester` /
`...parser`) — Research Mode does not re-implement ingestion. Everything
downstream of that point is separate: no 4-gate filter, no investigation
generation, no LLM call.

---

## Defining a topic profile

A `TopicProfile` (`cls_research.schemas.TopicProfile`) is a plain
dataclass, persisted as one JSON file per topic under `research/topics/`
(analyst-authored input, **committed to the repo** — unlike generated
dossiers, which are gitignored runtime output, same as `briefs/` and
`workspace/`).

| Field | Meaning |
|---|---|
| `topic_id` | Deterministic slug derived from `name` (e.g. `topic_dprk_missile_indigenization`) — not random, so the same topic always resolves to the same file/store. |
| `name` | Human-readable topic title. |
| `core_question` | The central research question. |
| `subquestions` | Specific questions the dossier should be able to answer. Each one that has no matching evidence is flagged as a collection gap (see below). |
| `keywords` | Bare terms to search for. |
| `entities` | Named entities (people, orgs, programs) to search for. |
| `geographies` | Place names — combined with keywords/entities to broaden coverage. |
| `time_horizon_days` | Only signals published within this window are collected. |
| `source_classes` | Which `spec1_labels.SOURCE_*` classes are in scope (e.g. `SOURCE_RSS`, `SOURCE_FARA`). Declaring a class the collector can't act on yet (anything but RSS, in this version) produces an explicit gap rather than silent omission. |
| `exclusions` | Case-insensitive substrings that, if present, drop an otherwise-matching item. |
| `aliases` | Analyst-declared synonyms, e.g. `{"DPRK": ["North Korea"]}`. The system never invents synonyms on its own. |
| `analyst_notes` | Free text — context for other analysts, not used by any logic. |

Example profiles: `research/topics/topic_dprk_missile_indigenization.json`
and `research/topics/topic_portland_metro_housing_levy_implementation.json`.

Build one in Python:

```python
from cls_research.schemas import TopicProfile
from cls_research.topics import save_topic_profile

profile = TopicProfile.new(
    name="Example Topic",
    core_question="What is actually happening with X?",
    keywords=["x", "x program"],
    entities=["Org Name"],
    geographies=["Region"],
    time_horizon_days=90,
    source_classes=["RSS"],
)
save_topic_profile(profile, base_dir="research/topics")
```

or hand-write the JSON file directly — the schema is the contract, not the
tooling.

---

## How it works

```
TopicProfile
     │
     ▼
expansion.expand_topic()        deterministic: lowercase, dedupe,
     │                          keyword×entity / keyword×geography /
     │                          entity×geography combinations, analyst
     │                          aliases, subquestions kept verbatim
     ▼
collector.collect_for_topic()   reuses spec1_core.signal.harvester +
     │                          .parser; substring-matches expanded terms
     │                          against parsed signal text; applies
     │                          time_horizon_days and exclusions; annotates
     │                          (never filters by) domain credibility
     ▼
dossier.build_dossier()         merges with the topic's prior dossier
     │                          version (if any); detects collection gaps;
     │                          diffs against the prior version for
     │                          notable findings
     ▼
store.DossierStore               appends the new version to
     │                          research/dossiers/<topic_id>.jsonl
     ▼
formatter.dossier_to_markdown   writes research/dossiers/<topic_id>/
                                 dossier_v<N>.md and dossier_latest.md
```

`pipeline.run_research()` is the single entrypoint that runs this whole
chain and persists the result.

### Query expansion — exactly what happens, no more

`expansion.expand_topic()` produces an ordered list of `ExpandedTerm`
objects, each tagged with the rule that produced it:

1. `keyword` — each keyword, lowercased
2. `entity` — each entity, lowercased
3. `subquestion` — each subquestion, kept as a full phrase
4. `alias` — every analyst-declared synonym
5. `keyword_x_entity` — every keyword combined with every entity
6. `keyword_x_geography` — every keyword combined with every geography
7. `entity_x_geography` — every entity combined with every geography

There is no ranking, no weighting, no embedding similarity. The same
profile always expands to the same term list, in the same order — see
`tests/test_research.py::test_expand_topic_is_deterministic`.

Matching against harvested text uses plain case-insensitive substring
containment (the same primitive `workspace.tracker` already uses to match
signals to case files) — not the two/three-word combination phrases, which
are kept in the dossier for transparency about intended coverage but are
too specific to usefully substring-match.

**Tip for writing profiles:** a single generic entity or keyword (e.g. "UN")
will match broadly across any general geopolitics feed. Favor more
specific multi-word keywords, and use `exclusions` to cut known false
positives — the dossier's `matched_terms` field always shows exactly which
term caused a match, so over-broad terms are easy to spot and tighten.

### Collection gaps — exactly what triggers one

A dossier's `unresolved_questions` list is populated by three explicit,
rule-based checks (`dossier._detect_gaps`):

- Zero items collected at all -> one top-level gap.
- A subquestion's own words (stopwords excluded) don't appear among any
  collected item's `matched_terms` -> that subquestion is flagged.
- A declared `source_classes` entry other than `SOURCE_RSS` -> flagged as
  "not yet wired into the collector," naming the specific class.
- Any feed that failed to harvest this run is named explicitly.

### Notable findings — a diff, not a summary

`notable_findings` is a deterministic diff against the topic's previous
dossier version: count of net-new items by `signal_id`, and any source
name that appears for the first time. On a topic's first run there is no
prior version, so the single entry is a coverage count instead.

---

## Running it

```bash
# One-off run for a topic
PYTHONPATH=src python -m spec1_core.tools.run_research \
    --topic research/topics/topic_dprk_missile_indigenization.json

# List every topic profile under research/topics/
PYTHONPATH=src python -m spec1_core.tools.run_research --list-topics

# Override the output location
PYTHONPATH=src python -m spec1_core.tools.run_research \
    --topic research/topics/<id>.json \
    --dossiers-dir generated/research/dossiers
```

Environment variable overrides (same pattern as `SPEC1_LEADS_PATH` /
`SPEC1_PSYOP_PATH`): `SPEC1_RESEARCH_TOPICS_DIR`, `SPEC1_RESEARCH_DOSSIERS_DIR`.

From Python:

```python
from cls_research.topics import load_topic_profile_by_id
from cls_research.pipeline import run_research

profile = load_topic_profile_by_id("topic_dprk_missile_indigenization")
artifact = run_research(profile)
```

If a Signal Mode cycle has already harvested signals this run, pass them
in directly to avoid a duplicate fetch of the same feeds:

```python
run_research(profile, signals=already_harvested_signals)
```

An MCP tool, `run_research`, is also exposed via `mcp_server.py` for
Claude-driven invocation (see that file for the full tool surface).

---

## What it produces

For each topic, two outputs:

- **`research/dossiers/<topic_id>.jsonl`** — append-only, one
  `ResearchArtifact` (dossier) version per run. This is the system of
  record, same convention as every other SPEC-1 store. **Gitignored** —
  it's runtime output, not a deliverable to commit (same as `briefs/`,
  `workspace/`).
- **`research/dossiers/<topic_id>/dossier_v<N>.md`** and
  **`dossier_latest.md`** — the human-readable rendering, with the
  dossier's sections kept separate: topic definition, notable findings,
  unresolved questions / collection gaps, collected items (table, with
  matched terms and credibility annotation per item), and provenance
  (sources scanned, this-run counts, harvest errors, time horizon).

A `ResearchArtifact` is also directly serializable via
`cls_research.formatter.dossier_to_json()`.

---

## Why no LLM and no scoring here

The brief said it directly: don't introduce opaque scoring,
auto-calibration, or black-box prioritization, and preserve deterministic
behavior, explicit logic, provenance, and human-in-the-loop judgment. A
first version that called an LLM for "notable findings" or scored items by
relevance would have been the easiest thing to build, and the wrong one
for this system — it would have made Research Mode the one place in
SPEC-1 where the analyst couldn't see why something was in (or missing
from) the dossier. Signal Mode already demonstrates the LLM-with-fallback
pattern (`spec1_core.briefing`) for the case where natural-language
synthesis is actually wanted; if Research Mode grows an optional
analyst-assist summarization step later, it should follow that exact
pattern — clearly labeled, always overridable, never load-bearing for
what gets collected.

---

## Recommended next improvements

In rough priority order:

1. **Feed selection per topic.** The collector currently harvests the same
   `DEFAULT_FEEDS` Signal Mode uses (defense/geopolitics RSS). A topic like
   the Portland housing-levy example will correctly produce zero matches
   against that feed set — it needs its own feed list. The natural fix is
   to let a `TopicProfile` reference `cls_osint.sources` by tag (e.g.
   match `geographies`/`keywords` against `OsintSource.tags`) instead of
   always pulling `DEFAULT_FEEDS`.
2. **Wire FARA / CONGRESSIONAL / NARRATIVE source classes into the
   collector.** Today only `SOURCE_RSS` is collectible; anything else
   declared in `source_classes` is an honest, explicit gap. `cls_osint`
   already has FARA/congressional/narrative adapters — extending the
   collector to query them for a topic's matched terms is the next
   logical step, without changing the dossier schema.
3. **SQLite dual-write for `DossierStore`**, matching the optional
   `db=` pattern already used by `LeadStore`/`PsyopStore`, once dossiers
   need to be queried (e.g. from `spec1_api`) rather than only read whole.
4. **A `/research` API surface and MCP tool parity**, mirroring
   `/leads`, `/brief`, etc., once Research Mode is used enough to justify
   programmatic access beyond the CLI.
5. **Per-item rather than per-signal-id dedup.** `build_dossier` dedupes
   accumulated items by `signal_id`; if the same story is republished
   under a new ID elsewhere, it will currently appear twice across
   versions. A content-hash dedup pass (reusing
   `spec1_core.signal.gates.score_novelty`'s bag-of-words cosine
   similarity, applied as a near-duplicate *annotation*, not a filter)
   would close that gap without introducing the kind of relevance
   black-box this design otherwise avoids.

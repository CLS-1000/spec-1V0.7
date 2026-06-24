# Research Mode Playbook

A practical guide to designing topics, running dossiers, and interpreting results.

---

## When to Use Research Mode

Use Research Mode when you need to:

- **Track a specific geopolitical topic over weeks/months** (e.g., "Chinese military exercises near Taiwan," "Russian Arctic activity," "DPRK weapons indigenization")
- **Monitor a legislative or regulatory action** (e.g., "Portland housing levy implementation," "EU AI Act enforcement")
- **Build a comprehensive picture of one actor** (e.g., "Chinese state-owned defense contractors," "Iranian GPU acquisition networks")
- **Answer standing analyst questions** that don't fit the daily Signal Mode cycle
- **Accumulate evidence for a case file** without losing older context to the daily archive

Do **not** use Research Mode for:

- Daily urgent intelligence (that's Signal Mode + leads)
- Real-time incident response (use workspace case files instead)
- One-off lookup ("what happened in the news today about X?")

---

## Part 1: Designing a Topic Profile

A `TopicProfile` is the analyst's contract with the system. Get it right, and dossiers will be precise and actionable. Get it wrong, and you'll drown in false positives or miss the story entirely.

### Step 1: Define the core question

**Bad:** "Everything about Russia"  
**Good:** "How is Russia using proxy forces to extend military reach in Africa?"

Write a question a colleague could read and immediately understand what the dossier should answer.

### Step 2: Brainstorm subquestions

These are the specific things the dossier should **be able to answer**. They become the basis for detecting collection gaps.

**Example (Sahel instability):**
```
Core question: How is extremist activity reshaping the geopolitical balance in the Sahel?

Subquestions:
- Which groups control territory, and where?
- What is the relationship between local groups and transnational organizations (AQ, ISIS)?
- How are regional powers (France, Russia, Turkey, Gulf states) positioning themselves?
- What role does migrant trafficking play in funding these groups?
- Which governments are losing control, and which are gaining it?
```

Each unanswered subquestion will appear in the dossier's `unresolved_questions` list.

### Step 3: Choose keywords

**Principle:** specific multi-word terms, not single words.

**Bad:** "Iran", "missile", "military"  
(These will match everything.)

**Good:** "Iranian ballistic missile test", "Shahed drone shipment", "Quds Force commander", "IRGC Aerospace Force"

**Tip:** Use exact names from recent public reporting. If a news story about your topic wouldn't use the keyword, skip it.

### Step 4: List entities

Named entities: people, organizations, programs, systems. These are the actors and objects in your story.

**Example (Russian defense):**
```
- Rostec
- Sergey Shoygu
- Russian Defense Ministry
- Orlan drone
- Kalibr cruise missile
- Uralvagonzavod
- United Aircraft Corporation
```

**Tip:** No abbreviations (the system won't auto-expand "UAV" to "unmanned aerial vehicle"). Write the full name. If an entity goes by multiple official names, add them to `aliases`.

### Step 5: Add geographies

Place names that, combined with your keywords/entities, sharpen the scope.

**Example (Chinese military expansion):**
```
- South China Sea
- Taiwan
- Spratly Islands
- Scarborough Shoal
- East China Sea
- Djibouti
- Belt and Road Initiative
```

**Tip:** Be specific. "China" is too broad. "Taiwan Strait," "Luzon Strait," "Miyako Strait" are better.

### Step 6: Set the time horizon

How far back should the dossier look? Default: 90 days.

- **Rapidly evolving topics** (active conflict, real-time sanctions): 14–30 days
- **Slower-moving structural issues** (economic sanctions, diplomatic positioning): 90–180 days
- **Long-term trends** (demographic shifts, industrial capacity): 180–365 days

The collector will only ingest signals published within this window from today.

### Step 7: Choose source classes

Which SPEC-1 sources should the collector query?

- **`SOURCE_RSS`** — always available (defense/geopolitics feeds)
- **`SOURCE_FARA`** — Foreign Agents Registration Act filings (foreign influence operations)
- **`SOURCE_CONGRESSIONAL`** — Congressional bills, hearings, votes
- **`SOURCE_NARRATIVE`** — curated narrative sources (coming soon)

If you declare a source class other than RSS, the dossier will flag it as a collection gap — honest about what you're missing.

**Example (Taiwan-focused):**
```json
"source_classes": ["SOURCE_RSS", "SOURCE_CONGRESSIONAL"]
```

(Congressional sources will let you track U.S. legislative response; RSS gets you defense reporting.)

### Step 8: Define exclusions

Case-insensitive substrings that, if present, drop an otherwise-matching item.

**Example (to avoid noise):**
```json
"exclusions": [
  "opinion",
  "analysis video",
  "cryptocurrency",
  "social media trend"
]
```

**Tip:** Start with zero exclusions, run the first dossier, then tighten based on false positives.

### Step 9: Declare aliases

Analyst-defined synonyms. The system never invents these on its own.

**Example:**
```json
"aliases": {
  "DPRK": ["North Korea", "Democratic People's Republic of Korea"],
  "IRGC": ["Islamic Revolutionary Guard Corps"],
  "PLA": ["People's Liberation Army", "Chinese military"]
}
```

### Step 10: Add analyst notes

Free text for yourself and colleagues: context, rationale, known limitations, standing questions.

**Example:**
```
"analyst_notes": "Created to track Russian positioning in Africa post-Ukraine invasion. Known gap: Russian-language sources not in our current feeds. Flag any coverage of GRU proxy activity."
```

---

## Part 2: Creating and Saving a Topic Profile

### Option A: Hand-write the JSON

Create a file: `research/topics/topic_<your_slug>.json`

**Template:**
```json
{
  "topic_id": "topic_sahel_extremism",
  "name": "Sahel Extremist Realignment",
  "core_question": "How is extremist activity reshaping the geopolitical balance in the Sahel?",
  "subquestions": [
    "Which groups control territory and where?",
    "What is the relationship between local and transnational groups?",
    "How are regional powers positioning themselves?"
  ],
  "keywords": [
    "Sahel extremism",
    "AQ Maghreb",
    "Islamic State Sahel",
    "Wagner Group Africa",
    "French military Mali",
    "Tuareg separatism"
  ],
  "entities": [
    "Al-Qaeda in the Islamic Maghreb (AQIM)",
    "Islamic State in the Greater Sahara (ISGS)",
    "Jama'at Nusrat al-Islam wa-l-Muslimin (JNIM)",
    "Wagner Group",
    "French Armed Forces",
    "Russian Defense Ministry"
  ],
  "geographies": [
    "Mali",
    "Burkina Faso",
    "Niger",
    "Sahel region",
    "West Africa"
  ],
  "time_horizon_days": 90,
  "source_classes": ["SOURCE_RSS", "SOURCE_CONGRESSIONAL"],
  "exclusions": ["opinion piece", "social media"],
  "aliases": {
    "AQIM": ["Al-Qaeda in the Islamic Maghreb"],
    "JNIM": ["Jama'at Nusrat al-Islam wa-l-Muslimin"]
  },
  "analyst_notes": "Tracking proxy warfare and power shifts in the Sahel. Gap: limited Arabic-language coverage in current feeds."
}
```

### Option B: Generate via Python

```python
from cls_research.schemas import TopicProfile
from cls_research.topics import save_topic_profile

profile = TopicProfile.new(
    name="Sahel Extremist Realignment",
    core_question="How is extremist activity reshaping the geopolitical balance in the Sahel?",
    subquestions=[
        "Which groups control territory and where?",
        "What is the relationship between local and transnational groups?",
    ],
    keywords=[
        "Sahel extremism",
        "AQ Maghreb",
        "Islamic State Sahel",
    ],
    entities=[
        "Al-Qaeda in the Islamic Maghreb (AQIM)",
        "Islamic State in the Greater Sahara (ISGS)",
    ],
    geographies=["Mali", "Burkina Faso", "Niger"],
    time_horizon_days=90,
    source_classes=["SOURCE_RSS", "SOURCE_CONGRESSIONAL"],
    exclusions=["opinion piece"],
    aliases={"AQIM": ["Al-Qaeda in the Islamic Maghreb"]},
    analyst_notes="Tracking proxy warfare in the Sahel.",
)

save_topic_profile(profile, base_dir="research/topics")
print(f"Saved: {profile.topic_id}")
```

---

## Part 3: Running Your First Dossier

### List all topics

```bash
PYTHONPATH=src python -m spec1_core.tools.run_research --list-topics
```

Output:
```
topic_sahel_extremism      Sahel Extremist Realignment (90 days, 3 subquestions)
topic_dprk_missiles        DPRK Missile Indigenization (120 days, 5 subquestions)
```

### Run a topic

```bash
PYTHONPATH=src python -m spec1_core.tools.run_research \
    --topic research/topics/topic_sahel_extremism.json
```

**What happens:**
1. Expands your keywords/entities/geographies deterministically
2. Queries the harvester for RSS (and other declared sources) going back 90 days
3. Substring-matches expanded terms against parsed signal text
4. Builds a dossier: new items, prior version, collection gaps, notable findings
5. Writes `research/dossiers/topic_sahel_extremism.jsonl` (append-only)
6. Renders to `research/dossiers/topic_sahel_extremism/dossier_latest.md`

### Check the output

```bash
# Latest dossier (human-readable)
cat research/dossiers/topic_sahel_extremism/dossier_latest.md

# All dossier versions (JSONL, for programmatic access)
cat research/dossiers/topic_sahel_extremism.jsonl | jq '.version, .collected_items | length'
```

---

## Part 4: Interpreting Dossier Output

### The markdown rendering

**Structure:**

```
# Sahel Extremist Realignment

**Run**: v1  
**Generated**: 2026-06-20  
**Time horizon**: 90 days (2026-03-22 to 2026-06-20)

---

## Topic Definition

Core question: How is extremist activity reshaping the geopolitical balance in the Sahel?

Subquestions:
- Which groups control territory and where?
- ...

---

## Notable Findings

This is the first run — 47 items collected.

---

## Unresolved Questions / Collection Gaps

- ❌ "What role does migrant trafficking play in funding?" — no matching items
- ⚠️  SOURCE_CONGRESSIONAL declared but not yet wired into collector
- ⚠️  Feed "Arabic news aggregator" failed to harvest this run

---

## Collected Items

| Source | Headline | Matched Terms | Credibility |
|--------|----------|---------------|-------------|
| DefenseNews | Wagner reports losses in Mali... | wagner group africa, mali | RSS |
| Reuters | AQIM claims responsibility for... | aqim, mali | RSS |

---

## Provenance

Feeds queried: DefenseNews, Jane's, Reuters, ...
Total items collected: 47
New items this run: 47 (first run)
Duplicates skipped: 0
```

### Reading the signals

**Matched Terms** column shows exactly which expanded term triggered the match. This is your audit trail.

- If it says "sahel extremism" (a keyword), the signal directly addresses your topic.
- If it says "mali" + "russia" (geography × entity), it's related but might be tangential.
- If you see weird matches, check your exclusions.

### Collection gaps

**Three types:**

1. **Subquestion unresolved** — none of the signal text contains words from a subquestion.  
   → Consider adding keywords or broadening geographies.

2. **Source class declared but not wired** — you said "SOURCE_CONGRESSIONAL" but the collector doesn't support it yet.  
   → Acknowledge the gap in your notes.

3. **Feed failed to harvest** — a data source returned an error.  
   → Usually temporary; re-run the dossier tomorrow.

---

## Part 5: Iterating on Your Topic

### After the first run

1. **Scan the dossier for false positives.** If keywords match lots of noise, refine them.
2. **Note which subquestions went unanswered.** Brainstorm new keywords/entities.
3. **Check matched terms.** If expansion combinations (e.g., "sahel" + "military") produce junk, add exclusions.

### Update your profile

Edit `research/topics/topic_sahel_extremism.json` with refinements:

```json
{
  ...
  "keywords": [
    "Sahel extremism",
    "AQIM operations Mali",
    "Islamic State Sahel",
    "Wagner Group Sahel"
  ],
  "exclusions": [
    "opinion piece",
    "social media trend",
    "cryptocurrency",
    "military video game"
  ],
  "analyst_notes": "v1 added: more specific keywords (e.g., 'AQIM operations Mali' instead of 'AQIM'). Excluded crypto/gaming noise."
}
```

### Re-run

```bash
PYTHONPATH=src python -m spec1_core.tools.run_research \
    --topic research/topics/topic_sahel_extremism.json
```

This appends a new version to the same `.jsonl` store. Older versions stay for posterity.

---

## Part 6: Integration with Signal Mode

### Workflow: from Signal Mode → Research Mode

1. **Daily Signal Mode run** harvests all feeds, generates brief + leads.
2. **You see a lead** relevant to an ongoing research topic.
3. **You run Research Mode** with `signals=` parameter to avoid re-harvesting:

```python
from spec1_engine.signal.harvester import harvest_feeds
from cls_research.topics import load_topic_profile_by_id
from cls_research.pipeline import run_research

signals = harvest_feeds()  # already done by Signal Mode
profile = load_topic_profile_by_id("topic_sahel_extremism")
artifact = run_research(profile, signals=signals)
```

This way, the dossier includes today's signals without duplicate network requests.

### Workflow: from Research Mode → leads

1. **You build a dossier** on a topic of strategic importance.
2. **The dossier surfaces a new actor** or significant event (in `notable_findings`).
3. **You manually create a lead** in `src/cls_leads/store.py` with a link back to the dossier.

Research Mode is the **analyst's deep dive**; leads are the **urgent surface**.

---

## Part 7: Best Practices & Anti-Patterns

### ✅ DO

- **Use full, proper names** for entities: "Islamic State in the Greater Sahara" not "ISIS" or "ISGS".
- **Write specific keywords.** "Chinese military drone program" beats "military" or "drone".
- **Test your profile on small time windows first** (7–14 days) to validate matching before running a full 90-day collection.
- **Review matched terms every run.** They're your quality control.
- **Version your profile in git.** `research/topics/` is committed to the repo; it's analyst knowledge, not runtime output.
- **Write clear subquestions.** Unanswered subquestions are the dossier's way of telling you what you're missing.

### ❌ DON'T

- **Use single words as keywords.** "Russia", "military", "China" will match everything.
- **Declare source classes you don't need.** `SOURCE_CONGRESSIONAL` is useful for legislative tracking but not relevant to every topic.
- **Leave exclusions empty** if you know there are known false positives. Tighten early.
- **Abandon a topic after one run.** Dossiers improve with iteration; each run adds context.
- **Rely on dossiers for urgent alerts.** That's Signal Mode + leads. Research Mode is for deliberate analysis.

---

## Part 8: Troubleshooting

### "My dossier is mostly empty (few matches)"

**Check:**
1. Are keywords/entities generic enough? "China" vs. "Coastal guard" — the second is more likely to match.
2. Is your time horizon too narrow? If set to 7 days and today is a weekend, you might miss a Friday story.
3. Are exclusions too aggressive? Temporarily set to `[]` and re-run.
4. Do the feeds you're querying actually cover your topic? RSS defaults are defense/geopolitics; a housing-levy topic won't match.

**Fix:** Use the CLI to test expansion:

```python
from cls_research.expansion import expand_topic
from cls_research.topics import load_topic_profile_by_id

profile = load_topic_profile_by_id("topic_sahel_extremism")
terms = expand_topic(profile)
for term in terms:
    print(f"{term.rule}: {term.term}")
```

This shows exactly what the system will search for. If you see obvious gaps, add keywords/entities.

### "Dossier has too much noise"

**Check:**
1. Are keywords too generic? "military" will match any defense story.
2. Are exclusions missing obvious false positives? "opinion", "video game", "cryptocurrency"?
3. Are matched terms being misapplied by geography combinations? ("Paris" + "Russia" might surface irrelevant diplomatic events.)

**Fix:** Add exclusions and re-run. The `matched_terms` column is your guide.

### "I want to query a source that's not RSS (e.g., FARA)"

This is a known gap. Declare the source class in your profile to be explicit:

```json
"source_classes": ["SOURCE_RSS", "SOURCE_FARA"]
```

The dossier will flag it as a collection gap. You can manually query FARA (via `cls_osint.adapters.fara`) and add findings to the dossier later.

---

## Part 9: Advanced Patterns

### Multi-region topic (China & Russia competition)

```json
{
  "topic_id": "topic_russia_china_arctic",
  "name": "Russian-Chinese Arctic Cooperation & Competition",
  "keywords": [
    "Arctic shipping",
    "Northern Sea Route",
    "Yamal LNG",
    "Chinese icebreaker",
    "Russian Arctic military",
    "Sino-Russian border"
  ],
  "entities": [
    "Gazprom",
    "China National Offshore Oil Corporation (CNOOC)",
    "Russian Arctic Command",
    "PLA Navy"
  ],
  "geographies": [
    "Arctic",
    "Siberia",
    "Northern Sea Route",
    "Russia",
    "China"
  ],
  "time_horizon_days": 180
}
```

### Legislative tracking (U.S. response to Chinese military expansion)

```json
{
  "topic_id": "topic_us_china_military_response",
  "name": "U.S. Legislative Response to Chinese Military Expansion",
  "keywords": [
    "Taiwan Defense Act",
    "Taiwan arms sales",
    "PLA ballistic missile",
    "South China Sea",
    "Quad partnership"
  ],
  "source_classes": ["SOURCE_RSS", "SOURCE_CONGRESSIONAL"],
  "time_horizon_days": 365
}
```

### Long-term monitoring (2+ years)

```json
{
  "time_horizon_days": 730,
  "analyst_notes": "Long-term trend analysis. Reviewing changes quarter-by-quarter."
}
```

---

## Part 10: Checklist Before First Run

- [ ] Topic name and core question are clear enough a colleague would immediately understand.
- [ ] Keywords are multi-word, specific phrases (not single words).
- [ ] Entities include full official names (not acronyms).
- [ ] Geographies are specific places (not continental-level).
- [ ] Subquestions are actual questions analysts want answered.
- [ ] Time horizon matches the pace of change (14 days for rapid events, 90+ for structural).
- [ ] Source classes reflect what you need (RSS is always available; others are optional).
- [ ] Exclusions catch known false positives (or start empty and add after first run).
- [ ] Aliases are analyst-provided (the system doesn't guess).
- [ ] JSON is valid (use `jq` to validate).
- [ ] Profile is saved under `research/topics/`.

---

## Part 11: MCP Integration

If you're using Claude via MCP, you can invoke Research Mode directly:

```
@spec1 run_research --topic topic_sahel_extremism
```

Claude will parse the dossier output and can help you interpret findings, draft memos, or suggest follow-up research directions.

---

## Reference: TopicProfile JSON Schema

```json
{
  "topic_id": "string (deterministic, auto-derived from name if omitted)",
  "name": "string (human-readable title)",
  "core_question": "string (the central research question)",
  "subquestions": ["string (analyst's specific questions to be answered)"],
  "keywords": ["string (multi-word search terms)"],
  "entities": ["string (proper names of actors/systems)"],
  "geographies": ["string (place names)"],
  "time_horizon_days": "integer (default: 90)",
  "source_classes": [
    "string (SOURCE_RSS | SOURCE_FARA | SOURCE_CONGRESSIONAL | SOURCE_NARRATIVE)"
  ],
  "exclusions": ["string (substrings that drop a signal if present)"],
  "aliases": {
    "string (canonical name)": ["string (alternative names)"]
  },
  "analyst_notes": "string (free-text context and known gaps)"
}
```

---

## Summary

Research Mode is **topic-driven, analyst-guided, deterministic, and accumulating**. Start with a clear question, define it precisely in a TopicProfile, run the dossier, iterate on keywords/exclusions based on results, and let it grow over weeks and months. Use it alongside Signal Mode (daily) and workspace case files (incident-specific) to build a comprehensive intelligence picture.


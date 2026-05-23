# SPEC-1 — Case Study

**Portfolio references:** [Landing page](https://mjlak1000.github.io/spec-1/) · [Portfolio summary](portfolio.md) · [README](../README.md)

## Who I am

I'm a career switcher. My work history is unusual for a software role: about seventeen years in restaurants and roughly two years at Apple retail during the original iPhone launch. I'm not pretending those add up to a CS degree. They add up to something different — a long stretch of operating under pressure, training people on systems they've never seen before, and triaging information faster than it arrives.

SPEC-1 is the artifact I built to show I can also think and ship like an engineer. Everything below is about what I decided and why — because in a portfolio project the *decisions* are the credential, not the line count.

## What SPEC-1 is

SPEC-1 is a real-time open-source intelligence (OSINT) platform. It harvests signals from RSS feeds, FARA filings, congressional records, and narrative sources; scores each signal through a four-gate framework; uses Claude to investigate and verify the survivors; analyzes outcomes; and produces a daily written intelligence brief. Everything is persisted twice — append-only JSONL for audit, SQLite for queries — and exposed both as a FastAPI HTTP service and as an MCP server so Claude can use the system as a tool.

The point was never the brief. The point was building a pipeline whose decisions I can defend.

## Engineering decisions worth talking about

### 1. A deterministic four-gate filter, not an ML classifier

The obvious move with this much text was to embed everything and rank by similarity. I didn't. Every signal has to clear four explicit gates — credibility, volume, velocity, novelty — each of them a rule I can read, change, and unit-test. When the system surfaces something wrong, I can point to the gate that failed and the threshold that was off. That's not possible with a model.

The tradeoff is that calibration is manual. The benefit is that calibration is *legible* — every threshold is a decision someone can argue with, and the test suite encodes which boundary cases were considered. For a system whose output is intended to inform human judgment, I'd rather be wrong in a way I can explain than right in a way I can't.

### 2. A frozen core with explicit governance

`src/spec1_core/core/` holds the canonical schemas, ID generation, logging utilities, and the prompt files. It is treated as off-limits to ad-hoc edits — agents (or future me) may import from it but not modify it without an explicit version bump and review. Every prompt in the system lives there as a `.md` file; no inline prompt strings allowed elsewhere.

This isn't paranoia. It's the lesson of seventeen years of operations: the parts of a system that everyone touches are the parts that drift. Pulling the contracts and the prompts out of the working surface and putting a fence around them is how you keep the system coherent as it grows.

### 3. Dual-write persistence — JSONL and SQLite

JSONL is the system of record: append-only, immutable, audit-friendly. SQLite is the query layer: indexed, fast, and easy to inspect, but it is secondary to the log. Where `cls_db.dual_write` is used, the write path is best-effort rather than atomic: JSONL is written first, then SQLite is attempted as a non-fatal cache/index update, so the two can diverge if the SQLite step fails. In practice, most stores are still JSONL-only today; dual-write is optional and currently has limited coverage rather than being universal across the system. The API reads through repository abstractions instead of depending on SQLite as the source of truth, so the database can be rebuilt from the log if needed.

I picked this because I wanted the durability story to be obvious: the source of truth is plain text on disk. The database is a convenience layer, not the canonical record. If anything ever looked off, I could `cat` a file and read it. That kind of inspectability is what I trust under pressure, and it's what lets the system survive me being wrong about something else later.

### 4. Test discipline as a calibration anchor

The repo has 1,009 collected pytest tests across 37 files — covering the engine, OSINT adapters, psyop detection, briefing, persistence, the API, the MCP server, the operator tools, and recent additions (legislative desk, PDX-1 metro module, LLM fallback, X publisher, workspace case management). Test coverage isn't the story — what's in the tests is. Most of them encode a specific decision: this is the threshold we chose, this is the boundary case it has to handle, this is the failure mode we don't want to regress.

When a calibration changes, the tests check that nothing else moved silently. That's the property I needed: I can adjust thresholds without lying awake wondering what I broke. The test suite also serves as a living record of which edge cases matter enough to document and defend.

## What the non-tech background actually buys you

I'm aware "I worked in restaurants" is not a tech credential. But there is a real overlap that's worth naming.

- **Triage under load.** The whole point of SPEC-1 is sorting too much information into the small subset that matters. That is, structurally, what every shift in a busy kitchen and every busy hour at an Apple Genius bar is. The pattern recognition transfers; only the domain changes.
- **Teaching brand-new tech.** Two years explaining the original iPhone to people who had never seen a capacitive touchscreen is two years of doing what good documentation does: meet someone where they are and walk them forward. That shows up in this repo as the README, the architecture diagrams, and the prompts in `core/prompts/`.
- **Operations literacy.** Knowing what fails when, and what you do when it does, is not learned from textbooks. The engineering decisions above — frozen contracts, dual-write durability, deterministic filtering — are operational decisions before they're technical ones. They reflect what I've learned about systems that have to keep running.

## Recent Operational Improvements

### Three-Tier LLM Fallback (`spec1_engine.llm`)

After a few cycles of production operation, I realized that every analysis point calling Claude exposed the whole system to a single-point-of-failure: API downtime, quota exhaustion, or cost spikes. The fix was to build a fallback chain: Claude Sonnet (primary), Ollama (local, free, offline-capable), rule-based templating (always available, zero latency).

This is not a technical problem; it's an operational one. The infrastructure must be resilient without being smart — the fallback outputs are deliberately worse, and the analyst knows to weight them accordingly. I protected this with tests so I never accidentally make the fallback smarter than it should be.

### Regional Intelligence (`cls_pdx1`)

Initially the system was purely national-scope. I added a Portland metro module to test whether the same four-gate framework applies to local political data. It does, but the data sources are different: OLIS (Oregon Legislature's live OData feed), ORESTAR (campaign finance), SEI (entity registry). Live data, not RSS.

The module revealed something operational: *my credibility weights are too coarse for local data*. A state legislator and a local city councilor carry different epistemic weight, but my four-gate framework treats them the same. This is fixable via calibration (add jurisdiction weight as a fifth dimension), but it's a data-driven discovery I wouldn't have made without a real use case.

### Workspace Case Management

The original design pushed all operator decisions onto external tools — you filed verdicts in a spreadsheet, ran calibration separately, lived with the fact that investigation notes had nowhere to live. Over time this became operationally painful. I built a CLI workspace (`spec1_engine.workspace`) so analysts can open cases, attach notes, file verdicts, and track investigation state without context-switching to a different tool.

It's a small thing, but it's how systems that actually work get built: by operators — even an operator of one — telling engineers what they need.

---

## What I'd do differently

Several things, honestly.

- **The four-gate weights are calibrated against a single observer — me.** Even though the feedback loop is now wired end to end (`cls_verdicts` captures human verdicts, `cls_calibration.aggregator` produces a reliability report, `cls_calibration.proposer` surfaces drift as suggested adjustments), every verdict in the dataset so far is mine. A real signal-vs-noise framework needs multiple reviewers to detect bias I can't see in my own judgment. The infrastructure exists; the social step doesn't yet.
- **The PDF export pipeline originally embedded `weasyprint` in-process** — native deps in the main process, real deployment friction. It's now isolated: `spec1_engine.tools.pdf_render` runs weasyprint as a subprocess so the main process never imports it and the native deps stay contained. That's how it should have started.
- **The frontend is a single static HTML file.** That was the right call for v0.4 — minimal blast radius, no build step, ships with the repo. A real version needs a proper SPA and a versioned API. I deferred both deliberately, but I know what they are.
- **The core governance violation.** In May 2026, I (via an agent) added four new prompt files directly to `src/spec1_engine/core/prompts/` without the human approval I documented as required. The prompts are working and the core is stable, but the violation is real. I should have either (a) gone through the approval process first, or (b) treated prompts as a non-core surface and moved them out. The rule exists for a reason — it keeps the system coherent as it grows.

## What I'm looking for

A team that's willing to read the code, look at the decisions, and judge them on their merits. I'm not the candidate with five years at FAANG. I'm the candidate who built a real system end-to-end, who can defend every decision in it, and who has spent two decades learning how to operate things that have to actually work.

I can ship code that gets decisions right, that survives contact with reality, and that remains legible six months later when you need to change it. I care about what breaks, why it breaks, and making sure it doesn't break the same way twice. That's all learned in restaurants and retail, not in computer science textbooks.

If that's a profile you can use, I'd like to talk.

— Matt Lakamp

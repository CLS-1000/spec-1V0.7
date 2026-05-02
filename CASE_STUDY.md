# SPEC-1 — Case Study

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

`src/spec1_engine/core/` holds the canonical schemas, ID generation, logging utilities, and the prompt files. It is treated as off-limits to ad-hoc edits — agents (or future me) may import from it but not modify it without an explicit version bump and review. Every prompt in the system lives there as a `.md` file; no inline prompt strings allowed elsewhere.

This isn't paranoia. It's the lesson of seventeen years of operations: the parts of a system that everyone touches are the parts that drift. Pulling the contracts and the prompts out of the working surface and putting a fence around them is how you keep the system coherent as it grows.

### 3. Dual-write persistence — JSONL and SQLite

JSONL is the system of record: append-only, immutable, audit-friendly. SQLite is the query layer: indexed, fast, easy to inspect. Every store writes both atomically through `cls_db.dual_write` so they cannot diverge. The API reads from JSONL via repository abstractions — never the database directly — so the database can be rebuilt from the log if it ever gets corrupted.

I picked this because I wanted the durability story to be obvious: the source of truth is plain text on disk. The database is a cache. If anything ever looked off, I could `cat` a file and read it. That kind of inspectability is what I trust under pressure, and it's what lets the system survive me being wrong about something else later.

### 4. Test discipline as a calibration anchor

The repo has 708 passing tests across the engine, OSINT adapters, psyop detection, briefing, persistence, the API, and the MCP server. Test coverage isn't the story — what's in the tests is. Most of them encode a specific decision: this is the threshold we chose, this is the boundary case it has to handle, this is the failure mode we don't want to regress.

When a calibration changes, the tests check that nothing else moved silently. That's the property I needed: I can adjust thresholds without lying awake wondering what I broke.

## What the non-tech background actually buys you

I'm aware "I worked in restaurants" is not a tech credential. But there is a real overlap that's worth naming.

- **Triage under load.** The whole point of SPEC-1 is sorting too much information into the small subset that matters. That is, structurally, what every shift in a busy kitchen and every busy hour at an Apple Genius bar is. The pattern recognition transfers; only the domain changes.
- **Teaching brand-new tech.** Two years explaining the original iPhone to people who had never seen a capacitive touchscreen is two years of doing what good documentation does: meet someone where they are and walk them forward. That shows up in this repo as the README, the architecture diagrams, and the prompts in `core/prompts/`.
- **Operations literacy.** Knowing what fails when, and what you do when it does, is not learned from textbooks. The engineering decisions above — frozen contracts, dual-write durability, deterministic filtering — are operational decisions before they're technical ones. They reflect what I've learned about systems that have to keep running.

## What I'd do differently

Several things, honestly.

- **The four-gate weights are calibrated against a single observer — me.** Even though the feedback loop is now wired end to end (`cls_verdicts` captures human verdicts, `cls_calibration.aggregator` produces a reliability report, `cls_calibration.proposer` surfaces drift as suggested adjustments), every verdict in the dataset so far is mine. A real signal-vs-noise framework needs multiple reviewers to detect bias I can't see in my own judgment. The infrastructure exists; the social step doesn't yet.
- **The PDF export pipeline depends on `weasyprint`, which carries native deps.** It's fine for a portfolio project; it would be a real deployment friction in production. A proper version would generate PDFs out of process.
- **The frontend is a single static HTML file.** That was the right call for v0.4 — minimal blast radius, no build step, ships with the repo. A real version needs a proper SPA and a versioned API. I deferred both deliberately, but I know what they are.

## What I'm looking for

A team that's willing to read the code, look at the decisions, and judge them on their merits. I'm not the candidate with five years at FAANG. I'm the candidate who built a real system end-to-end, who can defend every decision in it, and who has spent two decades learning how to operate things that have to actually work.

If that's a profile you can use, I'd like to talk.

— Matt Lakamp

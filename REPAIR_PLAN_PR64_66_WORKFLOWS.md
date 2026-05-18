# Repair Plan: Failed Workflows + PRs #64–#66

## Scope
- Audit failed workflow tasks and merged PRs #64, #65, #66.
- Define a repair plan for a follow-up implementation PR.

## Audit Findings

### 1) Failed workflow tasks
- **Workflow run `26006339875`** (`pages build and deployment`) failed in job `build`.
- Root cause from logs: **Jekyll build error** due to invalid YAML front matter in:
  - `briefs/spec1_brief_2026-04-14.md`
- A companion run (`26006349717`) was cancelled while the same pages build path was failing.

### 2) PR #64, #65, #66 status
- **No failed CI tasks on these merged PRs** (Python package and CodeQL checks were successful/neutral as expected).
- **No unresolved Git conflict markers** found in repository files (`<<<<<<<`, `=======`, `>>>>>>>`).

### 3) Conflict / risk items from merged PR content
- **PR #64** included generated brief files under `briefs/*latest*.md` alongside a security fix (mixed concern + generated artifact churn).
- **PR #65 and #66** both changed overlapping LLM-fallback files (`.env.example`, `tests/test_fallback_client.py`, `fallback_client.py`) on the same feature branch sequence; no merge conflict surfaced, but review notes indicate reliability/operability gaps worth hardening.

## Repair Plan (implementation PR)

1. **Fix Pages build break**
   - Remove Jekyll parsing exposure for operational brief artifacts by moving runtime brief outputs to `generated/briefs/` (gitignored) per repository policy.
   - Ensure Pages source only includes intended web assets.
   - Re-run pages workflow and confirm build/deploy success.

2. **Enforce generated-artifact policy**
   - Stop committing runtime/generated brief outputs to tracked source paths used by Pages; keep them in `generated/briefs/` or a dedicated generated branch.
   - Add a guard (CI or repository rule) that blocks future commits of generated brief/log artifacts in protected paths.

3. **Harden LLM fallback reliability (PR #65/#66 follow-up)**
   - Make Tier-2 preparation failures explicit and fast-fail to Tier-3 when model readiness fails.
   - Bound/avoid long blocking spawn/model-pull behavior during normal pipeline execution.
   - Align documented env vars so host/url configuration is unambiguous.

4. **Verification**
   - Run repository tests + lint gates.
   - Re-run affected workflows (Python package, Pages, CodeQL where applicable).
   - Confirm no regression in verifier behavior and no generated-artifact drift in tracked dirs.

## Exit Criteria
- Pages workflow green on `main`.
- No generated brief/log artifacts committed in protected source paths.
- LLM fallback behavior remains deterministic with passing tests.

# Current State: What Is Happening

## Situation

You are mid-execution of a CI fix. GitHub Actions on `develop` was hanging (exit 143 — SIGTERM) because tests call `verify_investigation` and `run_research` without mocking them, triggering live Claude API + Ollama calls with no timeout. The fix plan is in `Plans/adaptive-soaring-lovelace.md`. Steps 1 and 2 are done; Steps 3 and 4 are not.

---

## What Has Been Applied (committed + staged)

| Step | What | Status |
|------|------|--------|
| Step 1 | `pytest-timeout>=2.3` added to `pyproject.toml` + `timeout = 30` in ini | Done (uncommitted) |
| Step 2 | `OLLAMA_AUTO_SPAWN: "false"` added to CI workflow env | Done (uncommitted) |
| Step 4 (partial) | `test_cycle.py`: `test_verify_produces_outcome` now mocks `verifier.verify_investigation` | Done (uncommitted) |
| Step 4 (partial) | `test_cycle.py`: new import `from spec1_core.investigation import verifier` added | Done (uncommitted) |
| Step 4 (partial) | `test_cycle.py`: `test_run_cycle_updates_last_run_state` new test added | Done (uncommitted) |

All three changes are uncommitted, sitting in the working tree.

---

## What Is Still Missing

### `tests/test_cycle.py` — Step 3 incomplete
`run_research` is never mocked in cycle tests. Tests that call `run_cycle(...)` directly and reach the workspace step will make live API calls. Affected tests need:
```python
@patch("spec1_core.app.cycle.run_research", return_value=None)
```

### `tests/test_engine.py` — Step 4 incomplete (7 tests)
These tests call `verify_investigation` live:
- `test_verify_investigation_returns_outcome`
- `test_verify_outcome_confidence_range`
- `test_verify_outcome_valid_classification`
- `test_analyze_returns_intelligence_record`
- `test_analyze_record_confidence_range`
- `test_record_to_dict_complete`
- `test_analyze_with_no_analyst_leads_uses_default_weight`

All need `@patch("spec1_core.investigation.verifier.verify_investigation")` returning a minimal `Outcome`.

---

## What Comes Next (after CI is fixed)

`Plans/lets-fork-purring-lobster.md` — fork spec-1 into `/home/mjlak/congress-brief` and build `cls_congress/`: a federal legislative intelligence module (FEC, Congress.gov, LDA, Senate SEI) modeled on `cls_pdx1`. 10-step delivery order defined. Not started.

---

## Recommended Next Action

1. Complete Step 3 and 4 — mock `run_research` in `test_cycle.py` and `verify_investigation` in `test_engine.py`
2. Run `timeout 120 python -m pytest tests/test_engine.py tests/test_cycle.py -v --tb=short` to confirm no hangs
3. Run full suite `pytest tests/ -q --tb=short`
4. Commit all three files + push to `develop`
5. Then proceed to `congress-brief` fork

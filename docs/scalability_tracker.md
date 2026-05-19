# SPEC-1 Scalability Initiatives — Execution Tracker
Session-by-session breakdown + daily checklist

---

## OVERVIEW

- Total estimated time: ~20–25 hours over 5 work sessions
- Primary path: Linear (A → B → C → D → integration)
- Parallel quick wins: C (label audit) can run during A/B
- Risk: None (append-only + backward-compatible design)

---

## SESSION 1: Foundation (Storage Patterns)

**Goal:** Build scalable read layer; no data written yet  
**Estimated duration:** 4–5 hours  
**Exit criteria:** Cursor reader + indexed queries working, tests passing

### Pre-Session Checklist

- [ ] Clone latest `mjlak1000/spec-1` to `/tmp/spec-1`
- [ ] Verify existing `cls_db/dual_write.py` structure
- [ ] Review current test coverage in `tests/test_persistence.py`
- [ ] Check current JSONL file sizes in `data/` directory

### Tasks

#### T1.1: Implement `src/cls_db/cursor_reader.py`
**Time:** 45 min  
**Artifact:** `src/cls_db/cursor_reader.py` (~145 lines)

```bash
python -c "from cls_db.cursor_reader import Cursor, JSONLCursorReader; print('✓ Imports OK')"
```

Key decisions:
- [ ] Cursor is (timestamp, id) pair — confirmed as tiebreaker
- [ ] Chunk size default 1000 — overridable
- [ ] Line skipping graceful (JSON decode errors continue)
- [ ] EOF returns (records, None) not empty list

Validation:
```python
from cls_db.cursor_reader import Cursor
c = Cursor(start_ts="2026-05-19T10:00:00+00:00", start_id="r1")
assert c.from_string(c.to_string()).start_id == "r1"
```

---

#### T1.2: Implement `src/cls_db/indexed_queries.py`
**Time:** 30 min  
**Artifact:** `src/cls_db/indexed_queries.py` (~65 lines)

Key decisions:
- [ ] Use `Repository` interface (avoid duplicating DB logic)
- [ ] All queries ORDER BY written_at (append-only assumption)
- [ ] LIMIT parameter always enforced (no unbounded queries)
- [ ] Only SELECT queries; no mutations

---

#### T1.3: Add methods to `src/cls_db/dual_write.py`
**Time:** 15 min  
**Artifact:** `DualWriter.read_chunked()`, `DualWriter.indexed_queries()`

```python
def read_chunked(self, limit: int = 100):
    """Iterator over JSONL chunks."""
    from cls_db.cursor_reader import JSONLCursorReader
    reader = JSONLCursorReader(self.jsonl_path, chunk_size=limit)
    return reader.read_all_chunked(limit=limit)

def indexed_queries(self):
    """Get IndexedQueryLayer for this writer's backend."""
    from cls_db.indexed_queries import IndexedQueryLayer
    return IndexedQueryLayer(self.repo)
```

Backward compatibility check:
- [ ] Existing `read_jsonl()`, `read_db()` still work
- [ ] New methods are purely additive
- [ ] No changes to `write()` or `write_batch()`

---

#### T1.4: Create `tests/test_cursor_reader.py`
**Time:** 45 min  
**Artifact:** ~180 lines

```bash
pytest tests/test_cursor_reader.py -v
# Expected: 6 tests passing
```

Test names:
- `test_cursor_serialization` ✓
- `test_read_chunk_from_start` ✓
- `test_read_chunk_with_cursor` ✓
- `test_read_chunk_at_eof` ✓
- `test_read_all_chunked` ✓
- `test_malformed_json_graceful` ✓

---

#### T1.5: Create `tests/test_indexed_queries.py`
**Time:** 45 min  
**Artifact:** ~150 lines

```bash
pytest tests/test_indexed_queries.py -v
# Expected: 6 tests passing
```

Test names:
- `test_find_by_source` ✓
- `test_find_by_status` ✓
- `test_find_by_signal_type` ✓
- `test_find_since` ✓
- `test_find_recent` ✓
- `test_limit_respected` ✓

---

#### T1.6: Integration test (`tests/test_dual_write_scalable.py`)
**Time:** 30 min  
**Artifact:** ~100 lines

```python
def test_read_chunked_matches_full_read(tmp_path):
    """Verify chunked reader returns same records as full read."""
    dw = make_dual_writer(...)
    dw.write_batch([{"record_id": f"r{i}"} for i in range(250)])

    full = dw.read_jsonl()

    chunked = []
    for chunk in dw.read_chunked(limit=100):
        chunked.extend(chunk)

    assert len(full) == len(chunked)
    assert [r["record_id"] for r in full] == [r["record_id"] for r in chunked]
```

### Post-Session 1 Checklist

- [ ] All 14 tests passing (cursor reader + indexed queries + integration)
- [ ] Code coverage >90%
- [ ] No import errors; `PYTHONPATH=src pytest` runs clean
- [ ] Created 3 new files, edited 1 existing file

```bash
git add src/cls_db/{cursor_reader.py,indexed_queries.py} \
        tests/test_cursor_reader.py \
        tests/test_indexed_queries.py \
        tests/test_dual_write_scalable.py
git commit -m "feat(storage): add cursor-based pagination and indexed queries for JSONL"
git push
```

---

## SESSION 2: Dual-Write Expansion

**Goal:** Create migration infrastructure; build factories  
**Estimated duration:** 4 hours  
**Exit criteria:** Factories and migration tools working; backfill tested

### Pre-Session Checklist

- [ ] Session 1 tests all passing
- [ ] Review `spec1_engine/tools/generate_*.py` to understand write patterns
- [ ] Identify all JSONL write locations (`grep -r '.open("a")' src/`)
- [ ] Check current data sizes: `du -sh data/*.jsonl`

### Tasks

#### T2.1: Create `src/spec1_dual_write_config.py`
**Time:** 30 min  
**Artifact:** ~120 lines

```bash
python -c "from spec1_dual_write_config import get_intel_writer, get_leads_writer; print('✓')"
```

Key properties:
- [ ] Singletons (module-level `_WRITERS` dict)
- [ ] Lazy initialization (first access)
- [ ] Safe to call multiple times (same instance)
- [ ] `clear_all()` for testing

---

#### T2.2: Create `src/cls_db/migrate_jsonl_to_db.py`
**Time:** 45 min  
**Artifact:** ~110 lines

Key decisions:
- [ ] `skip_existing=True` is default (safe for re-runs)
- [ ] SQLite failure is non-fatal (JSONL is source of truth)
- [ ] Returns dict with counts (not exception on errors)
- [ ] `verify_parity` reports delta, not failure

---

#### T2.3: Create `tests/test_dual_write_coverage.py`
**Time:** 1 hour  
**Artifact:** ~200 lines

```bash
pytest tests/test_dual_write_coverage.py -v
# Expected: 8 tests passing
```

Test coverage:
- `test_get_intel_writer_singleton` ✓
- `test_get_leads_writer_singleton` ✓
- `test_get_brief_writer_singleton` ✓
- `test_get_psyop_writer_singleton` ✓
- `test_clear_all_resets` ✓
- `test_writers_independent` ✓
- `test_concurrent_access_safe` ✓
- `test_db_paths_unique` ✓

---

#### T2.4: Create `tests/test_migrate_jsonl_to_db.py`
**Time:** 1.5 hours  
**Artifact:** ~250 lines

```bash
pytest tests/test_migrate_jsonl_to_db.py -v
# Expected: 10 tests passing
```

Test coverage:
- `test_backfill_empty_jsonl` ✓
- `test_backfill_creates_db` ✓
- `test_backfill_inserts_all_records` ✓
- `test_backfill_skip_existing_true` ✓
- `test_backfill_skip_existing_false` ✓
- `test_backfill_idempotent` ✓
- `test_backfill_returns_correct_counts` ✓
- `test_verify_parity_match` ✓
- `test_verify_parity_delta` ✓
- `test_verify_parity_detects_mismatch` ✓

---

#### T2.5: Integration test (`tests/test_integration_dual_write_modules.py`)
**Time:** 1 hour  
**Artifact:** ~150 lines

```python
def test_backfill_real_signals_jsonl(tmp_path):
    signals_path = Path("data/signals.jsonl")
    if not signals_path.exists():
        pytest.skip("data/signals.jsonl not found")

    result = backfill_jsonl_to_db(
        jsonl_path=signals_path,
        db_path=tmp_path / "signals.db",
        table="signals"
    )

    parity = verify_parity(signals_path, tmp_path / "signals.db", "signals")
    assert parity["parity"] is True, f"Parity failed: {parity['delta']} records mismatch"


def test_indexed_queries_on_migrated_data(tmp_path):
    dw = make_dual_writer(
        jsonl_path=tmp_path / "test.jsonl",
        db_path=tmp_path / "test.db",
        table="signals"
    )
    records = [
        {"record_id": "s1", "source_type": "RSS", "status": "ACTIVE"},
        {"record_id": "s2", "source_type": "FARA", "status": "INACTIVE"},
    ]
    dw.write_batch(records)

    indexed = dw.indexed_queries()
    rss = indexed.find_by_source("RSS")
    assert len(rss) >= 1
    assert rss[0]["source_type"] == "RSS"
```

### Post-Session 2 Checklist

- [ ] All 18 new tests passing (factories + migration + integration)
- [ ] Backfill tool tested on synthetic data
- [ ] Code coverage >90%

```bash
git add src/spec1_dual_write_config.py \
        src/cls_db/migrate_jsonl_to_db.py \
        tests/test_dual_write_coverage.py \
        tests/test_migrate_jsonl_to_db.py \
        tests/test_integration_dual_write_modules.py
git commit -m "feat(dual-write): factory pattern and migration infrastructure"
git push
```

---

## SESSION 3: Label Unification + Module Updates

**Goal:** Unify all label strings; update module generators to use dual-write  
**Estimated duration:** 5 hours  
**Exit criteria:** Zero hardcoded label strings; all modules use DualWriter

### Pre-Session Checklist

- [ ] Sessions 1–2 complete
- [ ] `grep -r '"HIGH"' src/` to find all hardcoded priority strings
- [ ] Identify all write points in: `generate_leads.py`, `generate_brief.py`, `run_psyop.py`

### Tasks

#### T3.1: Label Audit (parallel — can start in Session 1)
**Time:** 1 hour

```bash
grep -rn '"HIGH"\|"CRITICAL"\|"MEDIUM"\|"LOW"' src/ --include="*.py" > label_audit.txt
grep -rn '"CLEAN"\|"HIGH_RISK"\|"MEDIUM_RISK"\|"LOW_RISK"' src/ --include="*.py" >> label_audit.txt

wc -l label_audit.txt
grep "cls_leads\|cls_psyop\|cls_world_brief" label_audit.txt | wc -l
```

Expected findings:
- `cls_leads/generator.py`: ~15 hardcoded priorities
- `cls_leads/formatter.py`: ~3 hardcoded priorities
- `cls_psyop/patterns.py`: ~8 hardcoded threats
- `cls_world_brief/*.py`: ~5 hardcoded labels

---

#### T3.2: Enhance `spec1_labels.py`
**Time:** 30 min  
**Artifact:** Add ~40 lines (validators)

```bash
python -c "
from spec1_labels import is_valid_priority, PRIORITY_HIGH
assert is_valid_priority('HIGH')
assert not is_valid_priority('INVALID')
print('✓ Validators OK')
"
```

---

#### T3.3: Replace hardcoded strings in `cls_leads/generator.py`
**Time:** 1.5 hours

```python
# Before:
([["escalation", "mobilization"], "HIGH", "MILITARY"],

# After:
([["escalation", "mobilization"], PRIORITY_HIGH, CATEGORY_MILITARY],

# Import:
from spec1_labels import PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, \
                         CATEGORY_MILITARY, CATEGORY_CYBER, CATEGORY_GEOPOLITICAL, CATEGORY_FARA, \
                         CATEGORY_PSYOP
```

```bash
pytest tests/test_leads.py -v
# Should pass (no logic change, just constants)
```

---

#### T3.4: Replace hardcoded strings in `cls_psyop/patterns.py`
**Time:** 1 hour

```python
# Before:
threat_level="HIGH"

# After:
threat_level=THREAT_HIGH

# Import:
from spec1_labels import THREAT_HIGH, THREAT_MEDIUM, THREAT_LOW, \
                         PSYOP_HIGH_RISK, PSYOP_MEDIUM_RISK, PSYOP_LOW_RISK, PSYOP_CLEAN
```

---

#### T3.5: Create `.github/scripts/check_hardcoded_labels.py`
**Time:** 30 min  
**Artifact:** CI check script

```bash
chmod +x .github/scripts/check_hardcoded_labels.py
python .github/scripts/check_hardcoded_labels.py
# Expected: "✓ No hardcoded label strings found"
```

---

#### T3.6: Create `tests/test_spec1_labels_compliance.py`
**Time:** 45 min  
**Artifact:** ~150 lines

```bash
pytest tests/test_spec1_labels_compliance.py -v
# Expected: 8 tests passing
```

Test coverage:
- `test_all_priorities_valid` ✓
- `test_all_threat_levels_valid` ✓
- `test_all_psyop_risks_valid` ✓
- `test_all_verifications_valid` ✓
- `test_is_valid_priority` ✓
- `test_is_valid_threat_level` ✓
- `test_is_valid_psyop_risk` ✓
- `test_is_valid_verification` ✓

---

#### T3.7: Update Module Generators to Use DualWriter
**Time:** 2 hours

```python
# src/spec1_engine/tools/generate_leads.py

# OLD:
def _write_lead(lead: dict):
    path = Path("data/leads.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(lead) + "\n")

# NEW:
def _write_lead(lead: dict):
    from spec1_dual_write_config import get_leads_writer
    dw = get_leads_writer(Path("db"))
    dw.write(lead)
```

Same pattern for:
- `generate_brief.py` → `get_brief_writer()`
- `run_psyop.py` → `get_psyop_writer()`
- `calibration_propose.py` → `get_intel_writer()`

### Post-Session 3 Checklist

- [ ] All hardcoded label strings replaced (CI check passes)
- [ ] All module generators updated to use DualWriter
- [ ] All tests passing
- [ ] Code coverage >90%
- [ ] Daily cycle still works

```bash
git add src/spec1_labels.py \
        src/spec1_engine/tools/generate_*.py \
        src/cls_leads/generator.py \
        src/cls_psyop/patterns.py \
        tests/test_spec1_labels_compliance.py \
        .github/scripts/check_hardcoded_labels.py
git commit -m "refactor: unify label constants and expand dual-write to all signal modules"
git push
```

---

## SESSION 4: CI Enhancement

**Goal:** Replace syntax-only linting with type-safe, secure pipeline  
**Estimated duration:** 3 hours  
**Exit criteria:** All CI gates enforced; pre-commit hook working locally

### Pre-Session Checklist

- [ ] Sessions 1–3 complete, all tests passing
- [ ] `pyproject.toml` ready for tool config additions
- [ ] Python 3.9+ confirmed as target version

### Tasks

#### T4.1: Install Quality Tools Locally
**Time:** 15 min

```bash
pip install ruff mypy bandit[toml] coverage pytest-cov pre-commit
ruff --version && mypy --version && bandit --version
```

---

#### T4.2: Update `pyproject.toml`
**Time:** 30 min  
**Artifact:** Add `[tool.*]` sections (~60 lines)

---

#### T4.3: Update `.github/workflows/python-package.yml`
**Time:** 45 min

Key changes:
- Add ruff (replaces flake8)
- Add mypy (new)
- Add bandit (new)
- Add coverage check (new; threshold 85%)
- Remove `exit-zero` from all lint steps

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/python-package.yml')); print('✓ YAML valid')"
```

---

#### T4.4: Create `.pre-commit-config.yaml`
**Time:** 30 min  
**Artifact:** ~40 lines

```bash
pre-commit install
pre-commit run --all-files
```

---

#### T4.5: Test CI Gates Locally
**Time:** 1 hour

```bash
ruff check src/ tests/ --select E,F,W,C901 --show-source
mypy src/ --strict --ignore-missing-imports
bandit -r src/ --severity-level medium
pytest --cov=src --cov-report=term-missing
coverage report --fail-under=85
```

**mypy strategy:** Add `# type: ignore` for legacy code; enforce types on new code only.

---

#### T4.6: Update `CONTRIBUTING.md`
**Time:** 30 min

Document quality gates: ruff, mypy, bandit, coverage, labels policy.

### Post-Session 4 Checklist

- [ ] ruff, mypy, bandit all passing
- [ ] Coverage ≥85%
- [ ] Pre-commit hook installed and working
- [ ] `.github/workflows/python-package.yml` updated
- [ ] `pyproject.toml` has all tool configs
- [ ] `.pre-commit-config.yaml` created

```bash
git add .github/workflows/python-package.yml \
        pyproject.toml \
        .pre-commit-config.yaml \
        CONTRIBUTING.md
git commit -m "ci: enforce type safety, security scanning, and coverage requirements"
git push
```

---

## SESSION 5: Integration & Validation

**Goal:** Verify all four initiatives work together; document; hand off  
**Estimated duration:** 2–3 hours  
**Exit criteria:** Full test suite passes; documentation complete; ready for production

### Pre-Session Checklist

- [ ] Sessions 1–4 all committed and pushed
- [ ] All GitHub Actions workflows succeeded
- [ ] Local `pytest` runs 100% passing
- [ ] Data backups available (if testing on live data)

### Tasks

#### T5.1: Full Integration Test
**Time:** 45 min

```bash
PYTHONPATH=src pytest --cov=src --cov-report=term

pytest tests/test_cursor_reader.py tests/test_indexed_queries.py -v           # A
pytest tests/test_dual_write_coverage.py tests/test_migrate_jsonl_to_db.py -v # B
pytest tests/test_spec1_labels_compliance.py -v                                # C
```

---

#### T5.2: Verify Architectural Invariants (`tests/test_architectural_invariants.py`)
**Time:** 30 min

```python
def test_append_only_invariant():
    """Verify JSONL is append-only (never modified)."""
    dw = make_dual_writer(...)
    dw.write({"record_id": "r1", "data": "original"})
    with open(dw.jsonl_path) as f:
        line1_first = f.read()

    dw.write({"record_id": "r2", "data": "new"})
    with open(dw.jsonl_path) as f:
        line1_second = f.read()

    assert line1_first in line1_second


def test_single_writer_enforced():
    """Verify only one writer per module."""
    from spec1_dual_write_config import get_leads_writer, clear_all

    w1 = get_leads_writer(Path("db"))
    w2 = get_leads_writer(Path("db"))
    assert w1 is w2

    clear_all()
    w3 = get_leads_writer(Path("db"))
    assert w1 is not w3
```

---

#### T5.3: Test Daily Cycle with New Infrastructure
**Time:** 1 hour

```bash
pytest tests/test_cycle.py -v -k "daily"
```

Verify:
- All signal modules write via DualWriter
- SQLite databases created in `db/` directory
- JSONL files still written (backward compat)
- Parity check passes

---

#### T5.4: Backfill Real Data (optional)
**Time:** 45 min ⚠️ Only if enabling SQLite queries in production

```bash
# Dry-run parity check
PYTHONPATH=src python -c "
from pathlib import Path
from cls_db.migrate_jsonl_to_db import verify_parity

for module in ['signals', 'leads', 'brief', 'psyop']:
    result = verify_parity(
        jsonl_path=Path(f'data/{module}.jsonl'),
        db_path=Path(f'db/{module}.db'),
        table=module
    )
    print(f'{module}: {result}')
"

# Actual backfill
PYTHONPATH=src python -c "
from pathlib import Path
from cls_db.migrate_jsonl_to_db import backfill_jsonl_to_db

for module in ['signals', 'leads', 'brief', 'psyop']:
    result = backfill_jsonl_to_db(
        jsonl_path=Path(f'data/{module}.jsonl'),
        db_path=Path(f'db/{module}.db'),
        table=module
    )
    print(f'{module}: inserted {result[\"inserted\"]}, skipped {result[\"skipped\"]}')
"
```

---

#### T5.5: Update Documentation
**Time:** 45 min

Files to update:
- `CLAUDE.md` — add "Storage Patterns" section; update dual-write docs
- `docs/architecture.md` — add scalable storage, dual-write, label unification, CI/CD sections
- `ROADMAP.md` — mark A/B/C/D complete; update next priorities
- `README.md` — note cursor-based pagination and indexed SQLite queries

---

#### T5.6: Final Validation

```bash
echo "=== INITIATIVE A: Storage Patterns ==="
pytest tests/test_cursor_reader.py tests/test_indexed_queries.py tests/test_dual_write_scalable.py -v

echo "=== INITIATIVE B: Dual-Write Expansion ==="
pytest tests/test_dual_write_coverage.py tests/test_migrate_jsonl_to_db.py tests/test_integration_dual_write_modules.py -v

echo "=== INITIATIVE C: Label Unification ==="
pytest tests/test_spec1_labels_compliance.py -v
python .github/scripts/check_hardcoded_labels.py

echo "=== INITIATIVE D: CI Enhancement ==="
ruff check src/ tests/ --select E,F,W,C901 --show-source
mypy src/ --strict --ignore-missing-imports
bandit -r src/ --severity-level medium
pytest --cov=src --cov-report=term
coverage report --fail-under=85
```

Expected:
```
✓ 14 tests (A)
✓ 10 tests (B)
✓  8 tests (C)
✓ CI checks pass (D)
✓ No hardcoded labels
✓ Coverage 85+%
```

### Post-Session 5 Checklist

- [ ] All 768 tests passing (736 original + 32 new)
- [ ] Coverage ≥85%
- [ ] All CI gates passing
- [ ] Pre-commit hook working
- [ ] Documentation updated (CLAUDE.md, docs/architecture.md, ROADMAP.md)
- [ ] Release notes created (`docs/RELEASE_NOTES_v0.4.md`)
- [ ] Data integrity verified (if backfilled)

```bash
git add docs/ CLAUDE.md ROADMAP.md README.md tests/test_architectural_invariants.py
git commit -m "docs: complete scalability initiatives v0.4 (storage, dual-write, labels, ci)"
git tag v0.4
git push --tags
```

---

## DAILY TRACKER TEMPLATE

```
Date: 2026-05-[XX]
Session: [#]
Duration: [H] hours
Estimated: [H] hours (delta: [±H])

Completed:
- [ ] T[X].Y: [Task name] (time: [m] min)
- [ ] T[X].Z: [Task name] (time: [m] min)

Blockers:
- None / [describe]

Next session prep:
- [Item 1]
- [Item 2]

Git commits:
- [hash]: [message]
```

---

## QUICK REFERENCE: FILE MANIFEST

### New Files (11 total)

| File | Lines |
|------|-------|
| `src/cls_db/cursor_reader.py` | 145 |
| `src/cls_db/indexed_queries.py` | 65 |
| `src/spec1_dual_write_config.py` | 120 |
| `src/cls_db/migrate_jsonl_to_db.py` | 110 |
| `tests/test_cursor_reader.py` | 180 |
| `tests/test_indexed_queries.py` | 150 |
| `tests/test_dual_write_coverage.py` | 200 |
| `tests/test_migrate_jsonl_to_db.py` | 250 |
| `tests/test_spec1_labels_compliance.py` | 150 |
| `.github/scripts/check_hardcoded_labels.py` | 60 |
| `.pre-commit-config.yaml` | 40 |

### Modified Files (10+ total)

| File | Change |
|------|--------|
| `src/cls_db/dual_write.py` | +20 lines |
| `src/spec1_labels.py` | +40 lines |
| `src/spec1_engine/tools/generate_leads.py` | ~30 lines |
| `src/spec1_engine/tools/generate_brief.py` | ~30 lines |
| `src/spec1_engine/tools/run_psyop.py` | ~30 lines |
| `src/spec1_engine/tools/calibration_propose.py` | ~30 lines |
| `src/cls_leads/generator.py` | ~20 lines |
| `src/cls_psyop/patterns.py` | ~20 lines |
| `.github/workflows/python-package.yml` | Rewritten |
| `pyproject.toml` | +60 lines |
| `CONTRIBUTING.md` | +30 lines |
| `docs/architecture.md` | +100 lines |
| `CLAUDE.md` | +50 lines |

**Total additions:** ~1,800 lines (mostly tests + tooling)  
**Deletions:** ~50 lines (removed `exit-zero` from CI)  
**Net change:** +1,750 lines

---

**Version:** 1.0  
**Last updated:** 2026-05-19  
**Status:** Ready for execution

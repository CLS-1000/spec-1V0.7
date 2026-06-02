# SPEC-1 Launch Plan

**Status:** ✅ READY TO LAUNCH  
**Approved:** 2026-05-22  
**Stakeholder:** User (mjlak1000)

---

## Launch Window

| Item | Value |
|------|-------|
| **Date** | 2026-05-23 (Friday) |
| **Time** | 14:00 UTC (07:00 PT) |
| **Duration window** | 14:00–16:00 UTC (1–2 hours) |
| **Rollback time** | <15 min (revert commit + redeploy) |
| **On-call owner** | User (mjlak1000) |
| **On-call shift** | 2026-05-23 14:00 UTC → 2026-05-24 14:00 UTC |

---

## Pre-Launch Checklist (24h before)

- [ ] Run full test suite: `pytest tests/ -q` (must pass all 4 Python versions in CI)
- [ ] Verify GitHub Pages renders: https://mjlak1000.github.io/spec-1/
- [ ] Check CI status: all workflows green for last 5 commits
- [ ] Review AUDIT_REPORT.md — confirm no new HIGH severity items
- [ ] Backup current `spec1_intelligence.jsonl` (copy to `spec1_intelligence.jsonl.pre-launch-backup`)
- [ ] Run one test cycle: `make cycle` → verify briefs generate correctly

---

## Launch Steps (in order)

### 1. Pre-flight (13:45 UTC)
```bash
# Verify environment is clean
git status                          # must be clean
git log --oneline -1               # confirm latest commit
python3 --version                  # confirm Python 3.9+
make test                           # full suite pass
```

### 2. Publish to Pages (13:50 UTC)
```bash
# Pages workflow deploys automatically on commit to main
# Just ensure portfolio HTML is current:
ls -l spec1_portfolio.html spec1_ui.html    # recent timestamps
```

### 3. Monitor (14:00–14:30 UTC)
- Watch GitHub Actions for any failures
- Confirm Pages deployed: https://mjlak1000.github.io/spec-1/
- Spot-check portfolio loads (no 404s, CSS renders)

### 4. Declare Launch (14:30 UTC)
- Post to repo: "🚀 SPEC-1 launched" issue comment with timestamp
- Update this file: change `Status` to `✅ LIVE`

### 5. On-call (14:30 UTC → next 24h)
- Monitor GitHub Actions: watch for failed cycles
- Respond to errors within 30 minutes
- If critical bug found: follow Rollback procedure below

---

## Rollback Procedure (if needed)

**Trigger:** Any deployment failure, data corruption, or API downtime >5 min

**Steps:**
```bash
# 1. Identify last good commit
git log --oneline | grep "✅" | head -1

# 2. Revert to last good state
git reset --hard <commit-hash>
git push origin main --force

# 3. GitHub Pages auto-redeploys within 30 sec

# 4. Document incident in INCIDENTS.md
```

**RTO:** ~2 minutes (push → Pages redeploy)  
**RPO:** Last git commit (no data loss)

---

## Success Criteria

✅ Launch is complete when:
1. All CI workflows passing
2. Portfolio pages rendering without errors
3. No manual interventions required for 1 hour post-launch
4. This file updated with `Status: ✅ LIVE`

---

## Post-Launch (Next 7 Days)

- [ ] Monitor error logs daily
- [ ] Confirm cycle runs are completing (check `spec1_intelligence.jsonl`)
- [ ] Get user feedback on portfolio UI/UX
- [ ] Plan Phase 2 improvements (alerting, monitoring, automation)

---

## Contact

**On-call:** User (mjlak1000)  
**Escalation:** (none specified; owner is also stakeholder)  
**Comms:** GitHub issues + commit messages

---

## Sign-off

- **Stakeholder:** User ✅
- **Launch date confirmed:** 2026-05-23 14:00 UTC ✅
- **On-call assigned:** User (mjlak1000) ✅

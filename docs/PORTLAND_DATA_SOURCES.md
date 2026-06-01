# Portland Data Sources — Phase 2 Expansion

**Status:** 🟡 ROADMAP (Post-Launch)  
**Priority:** HIGH — Core to PDX-1i mission  
**Timeline:** Q3 2026

---

## Currently Integrated (Live)

| Source | Type | Coverage | Status |
|--------|------|----------|--------|
| **OLIS** | Bills & Sponsors | Oregon State | ✅ Live (PR #260) |
| **ORESTAR** | Campaign Finance | Oregon State | ✅ Live (PR #260) |
| **TriMet** | Board & Contracts | Regional Transit | ✅ Live |
| **Metro** | Council & Planning | Regional | ✅ Live (demo) |

---

## Phase 2 Targets (Portland-Specific)

### Tier 1 — High Impact (Do First)

#### **#1: Portland City Council Voting Records**
- **Why:** Track voting patterns, detect coalitions, identify swing votes
- **Data source:** City of Portland Agenda & Minutes archives
- **Format:** PDF or structured HTML
- **Availability:** Public (City website)
- **Update:** Weekly (after council meetings)
- **Adapter approach:** Parse meeting minutes → extract votes
- **Integration:** Link votes to ORESTAR donations by council member
- **Legal:** Public records, no restriction

**Effort:** 4 hours | **Impact:** 🔴 HIGH | **Difficulty:** Medium

---

#### **#2: Multnomah County Property Records**
- **Why:** Detect undisclosed property holdings by public officials
- **Data source:** Multnomah County Assessor + County Mapping Dept
- **Format:** GIS shapefile or property database API
- **Availability:** Public (County GIS portal)
- **Update:** Quarterly (assessments)
- **Adapter approach:** Query by owner name → return properties
- **Integration:** Match officials against property owner database
- **Legal:** Public records; check terms of use

**Effort:** 6 hours | **Impact:** 🔴 HIGH | **Difficulty:** High (GIS data)

---

#### **#3: City of Portland Contracts & Procurement**
- **Why:** Track public money flows, vendor relationships, conflicts of interest
- **Data source:** Oregonbuy.cvo.oregon.gov or City procurement portal
- **Format:** CSV/database export or API
- **Availability:** Public (State procurement site)
- **Update:** Real-time (upon contract award)
- **Adapter approach:** Query contracts → filter by vendor/amount
- **Integration:** Identify officials' relatives or associates as vendors
- **Legal:** Public procurement data

**Effort:** 5 hours | **Impact:** 🔴 HIGH | **Difficulty:** Medium

---

### Tier 2 — Medium Impact (Phase 2B)

#### **#4: Portland Business License Registry**
- **Why:** Identify conflicts of interest (officials running businesses)
- **Data source:** City of Portland Business Services Office
- **Format:** Public records search or database dump
- **Availability:** Semi-public (searchable online)
- **Update:** Monthly
- **Adapter approach:** Search by owner name → return active licenses
- **Legal:** Public records (business ownership is disclosable)

**Effort:** 3 hours | **Impact:** 🟡 MEDIUM | **Difficulty:** Low

---

#### **#5: Portland Police Bureau Public Records**
- **Why:** Track accountability, use-of-force incidents, complaints
- **Data source:** Portland Police Bureau or PortlandPolice.org
- **Format:** Incident reports, complaint summaries
- **Availability:** FOIA/public records request (not API)
- **Update:** Monthly batch import
- **Adapter approach:** Ingest public incident summaries
- **Legal:** Public records; requires FOIA compliance

**Effort:** 8 hours | **Impact:** 🟡 MEDIUM | **Difficulty:** High (FOIA logistics)

---

#### **#6: FBI Portland Field Office**
- **Why:** Cross-reference federal investigations, indictments, and press releases involving Portland-area figures
- **Data source:** FBI.gov press releases (Portland division) + PACER federal court records
- **Format:** HTML/RSS
- **Availability:** Public
- **Update:** As-released
- **Adapter approach:** Monitor FBI Portland press release feed → extract named subjects
- **Integration:** Match subjects against known officials/entities in resolver
- **Legal:** Public records

**Effort:** 5 hours | **Impact:** 🟡 MEDIUM | **Difficulty:** Low

---

#### **#7: Portland Development Permits & Zoning**
- **Why:** Track development patterns, official approvals, conflicts
- **Data source:** Bureau of Development Services (BDS) or Portland Maps
- **Format:** GIS or database export
- **Availability:** Public (City GIS portal)
- **Update:** Real-time
- **Adapter approach:** Query by location → extract permits/approvals
- **Integration:** Identify officials involved in permit reviews
- **Legal:** Public records

**Effort:** 5 hours | **Impact:** 🟡 MEDIUM | **Difficulty:** Medium

---

### Tier 3 — Nice-to-Have (Phase 3)

| Source | Data | Use Case | Difficulty |
|--------|------|----------|------------|
| Portland Parks budget | Spending by park/program | Track resource allocation | Medium |
| TriMet ridership data | Passenger counts by line | Advocacy context | Low |
| PGE/NW Natural regulatory filings | Public utility disclosures | Infrastructure oversight | High |
| Portland Fire Bureau records | Incident reports, staffing | Emergency services analysis | Medium |
| County court records | Civil suits, judgments | Legal disputes | High (manual) |

---

## Implementation Strategy

### Phase 2A (Weeks 1-3 post-launch)
1. ✅ Document all source requirements (#7 task)
2. ▶️ Build City Council adapter (#1)
3. ▶️ Build contracts adapter (#3)
4. ▶️ Build business license adapter (#4)

**Effort:** ~12 hours | **Result:** 3 new sources live

---

### Phase 2B (Weeks 4-6)
5. ▶️ Build property records adapter (#2)
6. ▶️ Build development permits adapter (#6)

**Effort:** ~10 hours | **Result:** 2 more sources live

---

### Phase 3 (Q4 2026)
7. Police Bureau data (FOIA process)
8. FBI Portland Field Office feed
9. Utility regulatory filings
10. Court records integration

**Effort:** 20+ hours | **Result:** Full civic data mesh

---

## Data Architecture

### New Adapter Pattern
```python
# src/cls_pdx1/sources/portland_city_council.py
from cls_pdx1.sources.base import BaseAdapter, AdapterResult

class PortlandCityCouncilAdapter(BaseAdapter):
    source_name = "Portland City Council"
    
    def fetch(self) -> AdapterResult:
        # Fetch from City website or API
        # Parse voting records
        # Return list of Vote records
        pass
```

### New Models (if needed)
```python
class Vote(BaseModel):
    official_id: str
    official_name: str
    vote: Literal["yes", "no", "abstain"]
    motion_title: str
    voted_at: datetime
    source_uri: str
```

### Integration Points
- Link by official name → ORESTAR donations
- Link by location → metro/county governance
- Link by contract → vendor networks
- Link by property → asset holdings

---

## Legal & Attribution Requirements

| Source | License | Attribution | Terms |
|--------|---------|-------------|-------|
| City Council | Public domain | City of Portland | Public records |
| Property records | Public domain | County Assessor | Public records |
| Contracts | Public domain | Oregonbuy.cvo.oregon.gov | Public procurement |
| Business licenses | Public domain | City of Portland | Public records |
| Police records | FOIA | Portland PB | FOIA request |
| Development permits | Public domain | City of Portland | Public records |

**Action:** Verify each source's terms before implementation; document in brief footers.

---

## Success Criteria

✅ **Phase 2A complete when:**
- [ ] 3 new sources integrated (City Council, Contracts, Licenses)
- [ ] Tests pass for all 3 adapters
- [ ] Sample briefs generated using new data
- [ ] Zero MEDIUM/HIGH security issues

✅ **Phase 2B complete when:**
- [ ] 5 total new sources integrated
- [ ] Resolver matches officials across all sources
- [ ] "Conflict of Interest" briefs generated
- [ ] Coverage >80% on all adapters

---

## Post-Launch Tasks

```
#27: Document Portland data source requirements
#28: Add Portland City Council voting records adapter
#29: Add Portland contracts & procurement adapter
#30: Add Portland business license registry adapter
#31: Add Multnomah County property records adapter
#32: Add Portland development permits adapter
#33: Integrate all sources with resolver (cross-match)
#34: Generate conflict-of-interest intelligence briefs
#35: Expand test data with Portland records
```

---

## Roadmap Summary

| Phase | Timeline | Sources | Effort | Impact |
|-------|----------|---------|--------|--------|
| **Live** | 2026-05-23 | OLIS, ORESTAR, TriMet, Metro | ✅ Done | 🔴 HIGH |
| **2A** | 2026-06-13 | +City Council, Contracts, Licenses | 12h | 🔴 HIGH |
| **2B** | 2026-07-04 | +Property, Permits | 10h | 🟡 MED |
| **3** | 2026-10-01 | +Police, Utilities, Courts | 20h | 🟡 MED |

---

## Success Vision

By end of Q3 2026, PDX-1i will provide:

✅ **Complete civic network** — Every Portland official linked to:
- Campaign donations (ORESTAR)
- Votes & positions (City Council records)
- Property holdings (County assessor)
- Business interests (License registry)
- Public contracts (Procurement)
- Development approvals (BDS)

✅ **Automated conflict detection** — Briefs highlight:
- Officials voting on contracts where they have financial interest
- Votes influenced by major donors
- Property zoning decisions tied to owner holdings
- Undisclosed business operations

✅ **Complete accountability** — Trail from decision → money → official

---

**Ready to launch Phase 2?** See tasks #27-35 in task list.

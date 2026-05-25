# PDX-1i DATA MODEL SCHEMA

**Version:** 1.0  
**Last Updated:** May 2026  
**Module:** cls_pdx1 (PDX-1i Metro Citizens Brief)

---

## Core Principle

> Every record must carry provenance (source_uri + timestamp). Nothing enters without evidence.

---

## 1. Official

```json
{
  "id": "off:portland:keith-wilson",
  "name": "Keith Wilson",
  "role": "Mayor of Portland",
  "district_id": "dist:portland:citywide",
  "jurisdiction": "Portland",
  "term_start": "2025-01-01",
  "term_end": "2028-12-31",
  "verified": true,
  "confidence": 0.95,
  "sources": ["https://portland.gov/..."],
  "notes": "Current mayor as of May 2026"
}
```

---

## 2. Entity

```json
{
  "id": "ent:pge",
  "name": "Portland General Electric",
  "type": "Utility",
  "sector": "Energy",
  "location": "Portland Metro",
  "watch_listed": true,
  "verified": true,
  "confidence": 0.90,
  "sources": ["https://portlandgeneral.com/..."]
}
```

---

## 3. District

```json
{
  "id": "dist:portland:citywide",
  "name": "Portland Citywide",
  "type": "City Council",
  "jurisdiction": "Portland",
  "population": 652503,
  "verified": true
}
```

---

## 4. Affiliation (Relationship)

```json
{
  "id": "aff:keith-wilson-pge-2026-05",
  "from": "off:portland:keith-wilson",
  "to": "ent:pge",
  "type": "DONATION",
  "amount": 2500,
  "date": "2026-03-15",
  "confidence": 0.85,
  "verified": true,
  "source_uri": "https://oregon.gov/orest...",
  "notes": "Campaign contribution"
}
```

**Allowed Types:** `DONATION`, `BOARD_SEAT`, `LOBBYING`, `CONTRACT`, `POLICY_INTERACTION`, `REPRESENTS`

---

## 5. Signal

```json
{
  "id": "sig:pge-donation-spike-2026-05",
  "entity_id": "ent:pge",
  "type": "DONATION_SPIKE",
  "value": 45000,
  "baseline_90day": 12000,
  "sigma": 3.2,
  "tier": 1,
  "date": "2026-05-20",
  "verified": false,
  "confidence": 0.72
}
```

**Tier System:**
- Tier 1: >3σ or hard signal → Immediate attention
- Tier 2: 2–3σ
- Tier 3: 1–2σ
- Tier 4: <1σ (monitor)

---

## 6. Anomaly

```json
{
  "id": "anom:pge-2026-05-20",
  "signal_id": "sig:pge-donation-spike-2026-05",
  "entity_id": "ent:pge",
  "description": "Donation volume 3.2σ above 90-day baseline",
  "tier": 1,
  "published": false,
  "created_at": "2026-05-24T14:22:00Z"
}
```

---

## 7. Issue (Metro Citizens Brief)

```json
{
  "id": "issue:2026-05-24",
  "date": "2026-05-24",
  "title": "Metro Citizens Brief — May 24, 2026",
  "sections": [
    {
      "title": "Elevated Signals",
      "content": "...",
      "anomalies": ["anom:pge-2026-05-20"]
    }
  ],
  "diagram_snapshot": "...",
  "published": true
}
```

---

## Relationship Summary

- **Official** → **District** (represents)
- **Official** ↔ **Entity** (via Affiliation)
- **Entity** → **Signal** → **Anomaly**
- **Anomaly** → **Issue** (published in brief)

---

**All models enforce:**
- `verified` flag
- `confidence` score (0.0–1.0)
- `source_uri` (provenance)
- Append-only design

> The system surfaces evidence. The analyst draws conclusions.
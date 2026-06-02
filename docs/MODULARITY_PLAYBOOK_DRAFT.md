# The SPEC-1 Modularity Playbook (Draft for External Use)

**How to build a new high-fidelity intelligence desk without starting from zero.**

This is the real leverage.

---

## The Core Pattern

Every serious intelligence product in SPEC-1 follows the same shape:

1. **Schemas** — Clean domain models (dataclasses or Pydantic) with stable IDs.
2. **Sources / Adapters** — One or more data ingestors with clear failure handling.
3. **Validation** — The 4-gate system (or a domain-specific version of it).
4. **Processing Layer** — Whatever turns raw signals into structured insight (neutrality, anomaly, scoring, etc.).
5. **Publication** — PDF, X thread, email, API, or whatever the audience needs.
6. **Store + Dual-Write** — JSONL as source of truth, optional relational layer.
7. **Calibration Hook** — Way for humans to correct and improve the system over time.

The magic is that these pieces are loosely coupled enough that you can swap or add them without rewriting everything.

---

## How to Stand Up a New Desk (The 80/20 Version)

1. Copy the folder structure from an existing mature product (cls_pdx1 is the richest example).
2. Implement your adapters against the BaseAdapter pattern.
3. Wire them into a Pipeline class that collects signals + anomalies.
4. Run them through the existing 4-gate + any domain-specific gates.
5. Feed the survivors into your publication generator (start by forking the existing one and adapting the sections).
6. Add a store that uses DualWriter if you want persistence.
7. Expose it via the API router pattern if you want it on the web/MCP surface.

You now have a new intelligence product that inherits the determinism, auditability, and failure tolerance of the whole system.

---

## Why This Matters at Scale

Most people who want to do serious regional or domain intelligence work have to start from scratch every time. That is why almost nothing at this level of rigor exists outside of well-funded state actors.

The modular pattern removes that tax.

The next serious person who wants to do this for their city, their issue area, or their vertical can stand on what already exists instead of rebuilding the foundation.

That is how you get from one node (Portland) to a network.

---

*This is the real product. Not just the briefs. The ability to spin up new high-quality nodes quickly and consistently.*

---

**Use this. Improve it. Make the next version better than this one.**
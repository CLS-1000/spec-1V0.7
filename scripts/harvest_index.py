#!/usr/bin/env python3
# @domain: spec-1
# @module: harvest_index
# @loc: gh_main
# @status: stable
# @depends: NONE

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

REPO_ROOT = Path(__file__).parent.parent
OUTPUT = REPO_ROOT / "INDEX.md"
EXTENSIONS = {".py", ".sh", ".sql", ".yaml", ".toml", ".md", ".cfg", ".ini"}
SKIP_DIRS = {"_ARCHIVE", ".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
TAG_PATTERN = re.compile(r"#\s*@(\w+):\s*(.+)")
STATUS_ORDER = ["stable", "testing", "drafting", "deprecated"]

# Explicit domain tag aliases: old/variant -> canonical
DOMAIN_ALIASES = {
            "citizens_source":      "notitia_civica",
            "citizens_cognisance":  "notitia_civica",
            "citizen_cognisance":   "notitia_civica",
            "notitia":              "notitia_civica",
            "pdx":                  "notitia_civica",
            "portland":             "notitia_civica",
            "metro":                "notitia_civica",
            "cls_pdx":              "notitia_civica",
            "cls_pdx1":             "notitia_civica",
}

# Path fragments that imply notitia_civica ownership
# Used when a file has no @domain tag OR its tag is untagged/ambiguous
NOTITIA_PATH_KEYWORDS = re.compile(
            r"(cls_pdx|pdx1|pdx_|portland|metro|olis|orestar|sei|wa_pdc|trimet|ppb|"
            r"nw_natural|ohsu|pge|schnitzer|water_bureau|notitia)",
            re.IGNORECASE,
)


def infer_domain(tags: dict, filepath: Path) -> str:
            """Return the canonical domain for a file.

                Priority order:
                    1. Explicit @domain tag (after alias normalisation)
                        2. Path-based inference for notitia_civica keywords
                            3. 'untagged' fallback
                                """
            raw = tags.get("domain", "")
            if raw:
                            return DOMAIN_ALIASES.get(raw, raw)
                        # No tag — check path
                        path_str = str(filepath)
    if NOTITIA_PATH_KEYWORDS.search(path_str):
                    return "notitia_civica"
                return "untagged"


def extract_tags(filepath):
            tags = {}
    try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                        for i, line in enumerate(f):
                                                                if i > 25:
                                                                                            break
                                                                                        m = TAG_PATTERN.match(line.strip())
                                                                if m:
                                                                                            tags[m.group(1)] = m.group(2).strip()
    except Exception:
        pass
    return tags


def harvest(filter_domain=None, filter_status=None, filter_loc=None):
            entries = []
    for root, dirs, files in os.walk(REPO_ROOT):
                    dirs[:] = sorted([d for d in dirs if d not in SKIP_DIRS])
                    for fname in sorted(files):
                                        fpath = Path(root) / fname
                                        if fpath.suffix not in EXTENSIONS:
                                                                continue
                                                            rel = fpath.relative_to(REPO_ROOT)
                                        tags = extract_tags(fpath)
                                        if not tags:
                                                                continue
                                                            # Resolve canonical domain and write back into tags dict
                                                            tags["domain"] = infer_domain(tags, rel)
                                        if filter_domain and tags["domain"] != filter_domain:
                                                                continue
                                                            if filter_status and tags.get("status", "") != filter_status:
                                                                                    continue
                                                                                if filter_loc and tags.get("loc", "") != filter_loc:
                                                                                                        continue
                                                                                                    entries.append((rel, tags))
                                return entries


def build_reverse_index(entries):
            """Build module -> list of (dependent_module, dependent_path) map."""
    module_map = {}
    for rel, tags in entries:
                    mod = tags.get("module", "")
        if mod:
                            module_map[mod] = str(rel)

    reverse = defaultdict(list)
    for rel, tags in entries:
                    mod = tags.get("module", "")
        depends_raw = tags.get("depends", "NONE")
        if depends_raw in ("NONE", "—", "", "-"):
                            continue
                        deps = re.split(r"[,/]", depends_raw)
        for dep in deps:
                            dep = dep.strip()
                            if not dep:
                                                    continue
                                                dep_key = Path(dep).stem.replace("-", "_")
            reverse[dep_key].append((mod or str(rel), str(rel)))
    return reverse


def write_index(entries):
            by_domain = {}
    for rel, tags in entries:
                    domain = tags.get("domain", "untagged")
        if domain not in by_domain:
                            by_domain[domain] = []
        by_domain[domain].append((rel, tags))

    for domain in by_domain:
                    by_domain[domain].sort(key=lambda x: (
                                        STATUS_ORDER.index(x[1].get("status", "drafting"))
                                        if x[1].get("status", "drafting") in STATUS_ORDER else 99,
                                        x[1].get("module", str(x[0]))
                    ))

    scratch_items = [(rel, tags) for rel, tags in entries if tags.get("loc", "") == "_SCRATCH"]
    reverse_index = build_reverse_index(entries)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append("# SPEC-1 INDEX\n")
    lines.append("> Auto-generated by `scripts/harvest_index.py`. Do not edit manually.\n")
    lines.append(f"\nGenerated: {now}  \n")
    lines.append(f"Indexed: **{len(entries)} tagged files** across **{len(by_domain)} domains**\n")
    lines.append("\n---\n")

    # --- Concept Matrix ---
    lines.append("## Concept Matrix\n")
    header = f"{'domain':<25} {'total':>6} {'stable':>8} {'testing':>9} {'drafting':>10} {'_SCRATCH':>10}"
    lines.append(header + "\n")
    lines.append("-" * 75 + "\n")
    for domain in sorted(by_domain):
                    items = by_domain[domain]
        total = len(items)
        stable = sum(1 for _, t in items if t.get("status") == "stable")
        testing = sum(1 for _, t in items if t.get("status") == "testing")
        drafting = sum(1 for _, t in items if t.get("status") == "drafting")
        scratch = sum(1 for _, t in items if t.get("loc") == "_SCRATCH")
        lines.append(f"{domain:<25} {total:>6} {stable:>8} {testing:>9} {drafting:>10} {scratch:>10}\n")
    lines.append("\n---\n")

    # --- Domain sections ---
    for domain in sorted(by_domain):
                    lines.append(f"## {domain}\n")
        lines.append(f"{'module':<40} {'loc':<12} {'status':<12} {'depends':<35} path\n")
        lines.append("-" * 130 + "\n")
        for rel, tags in by_domain[domain]:
                            mod = tags.get("module", "—")
            loc = tags.get("loc", "—")
            status = tags.get("status", "—")
            depends = tags.get("depends", "NONE")
            lines.append(f"{mod:<40} {loc:<12} {status:<12} {depends:<35} {rel}\n")
        lines.append("\n")

    # --- Reverse Dependency Index ---
    lines.append("---\n")
    lines.append("## Reverse Dependency Index\n")
    lines.append("> For each module: which other modules declare it in `@depends`.\n\n")
    if not reverse_index:
                    lines.append("_No cross-module dependencies detected._\n")
else:
        for dep_key in sorted(reverse_index.keys()):
                            dependents = reverse_index[dep_key]
            lines.append(f"### `{dep_key}`\n")
            lines.append(f"{'dependent module':<40} path\n")
            lines.append("-" * 80 + "\n")
            for dep_mod, dep_path in sorted(dependents):
                                    lines.append(f"{dep_mod:<40} {dep_path}\n")
                                lines.append("\n")

    # --- Open Work Queue ---
    lines.append("---\n")
    lines.append("## Open Work Queue\n")
    lines.append("> Files pending promotion to `gh_main`.\n\n")
    if scratch_items:
                    lines.append(f"{'module':<40} {'domain':<25} {'status':<12} path\n")
        lines.append("-" * 115 + "\n")
        for rel, tags in scratch_items:
                            mod = tags.get("module", "—")
            domain = tags.get("domain", "untagged")
            status = tags.get("status", "—")
            lines.append(f"{mod:<40} {domain:<25} {status:<12} {rel}\n")
else:
        lines.append("_Queue is clear._\n")

    OUTPUT.write_text("".join(lines), encoding="utf-8")
    print(f"[OK] INDEX.md written — {len(entries)} files / {len(by_domain)} domains")
    if scratch_items:
                    print(f"[!!] {len(scratch_items)} file(s) pending promotion to gh_main")
    if reverse_index:
                    print(f"[OK] Reverse index built — {len(reverse_index)} depended-on module(s) mapped")


def print_matrix(entries):
            by_domain = {}
    for rel, tags in entries:
                    domain = tags.get("domain", "untagged")
        by_domain.setdefault(domain, []).append((rel, tags))

    print(f"\n{'DOMAIN':<20} {'MODULE':<30} {'LOC':<15} {'STATUS'}")
    print("-" * 80)
    for domain in sorted(by_domain):
                    for rel, tags in by_domain[domain]:
                                        print(
                                                                f"{tags.get('domain', '_'):<20} "
                                                                f"{tags.get('module', str(rel)):<30} "
                                                                f"{tags.get('loc', '_'):<15} "
                                                                f"{tags.get('status', '_')}"
                                        )


if __name__ == "__main__":
            parser = argparse.ArgumentParser(description="Harvest SPEC-1 codebase index")
    parser.add_argument("--domain", help="Filter by domain")
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--loc", help="Filter by loc")
    parser.add_argument("--print", action="store_true", help="Print to stdout only")
    args = parser.parse_args()

    results = harvest(
                    filter_domain=args.domain,
                    filter_status=args.status,
                    filter_loc=args.loc,
    )

    if not results:
                    print("[WARN] No tagged files found matching filters.")
        sys.exit(0)

    if args.print:
                    print_matrix(results)
else:
        write_index(results)

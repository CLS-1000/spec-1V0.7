# @domain:   product
# @module:   expansion
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Deterministic query expansion for Research Mode.

Every expansion rule here is a fixed, explicit transformation — there is no
embedding similarity, no learned synonym model, and no weighting of one
term over another. The output is an ordered, de-duplicated list of
:class:`ExpandedTerm`, each tagged with the rule that produced it and the
profile field(s) it was derived from, so the full expansion is auditable
from the dossier alone.

Rules applied, in this order:
  1. keyword     — each ``profile.keywords`` entry, normalised
  2. entity      — each ``profile.entities`` entry, normalised
  3. subquestion — each ``profile.subquestions`` entry, normalised (kept as
                   a whole phrase — sub-questions are matched as the
                   question text itself, not tokenised)
  4. alias       — every synonym declared in ``profile.aliases`` (analyst-
                   supplied only; the system never invents synonyms)
  5. keyword_x_entity     — every keyword combined with every entity
  6. keyword_x_geography  — every keyword combined with every geography
  7. entity_x_geography   — every entity combined with every geography

Combination rules (5-7) are bounded by the size of the profile's own lists,
so coverage scales with how much the analyst has actually specified —
there is no combinatorial blow-up beyond what the profile itself describes.
"""

from __future__ import annotations

from spec1_core.signal.parser import STOPWORDS
from spec1_labels import (
    EXPANSION_RULE_ALIAS,
    EXPANSION_RULE_ENTITY,
    EXPANSION_RULE_ENTITY_X_GEO,
    EXPANSION_RULE_KEYWORD,
    EXPANSION_RULE_KEYWORD_X_ENTITY,
    EXPANSION_RULE_KEYWORD_X_GEO,
    EXPANSION_RULE_SUBQUESTION,
)

from cls_research.schemas import ExpandedTerm, TopicProfile


def _norm(text: str) -> str:
    """Lowercase + collapse whitespace. The only normalisation applied —
    no stemming, no spelling correction, nothing that could silently change
    what an analyst typed."""
    return " ".join(text.strip().lower().split())


def expand_topic(profile: TopicProfile) -> list[ExpandedTerm]:
    """Deterministically expand a TopicProfile into a list of search terms.

    Same profile in -> same ordered term list out, every time. Order is
    stable (rule order above, then input order within a rule) so two runs
    against an unchanged profile are byte-for-byte comparable.
    """
    terms: list[ExpandedTerm] = []
    seen: set[tuple[str, str]] = set()  # (rule, term) — same text can appear under >1 rule

    def _add(term: str, rule: str, derived_from: list[str]) -> None:
        norm = _norm(term)
        if not norm:
            return
        key = (rule, norm)
        if key in seen:
            return
        seen.add(key)
        terms.append(ExpandedTerm(term=norm, rule=rule, derived_from=list(derived_from)))

    keywords = [k for k in profile.keywords if k]
    entities = [e for e in profile.entities if e]
    geographies = [g for g in profile.geographies if g]

    # 1. keywords
    for kw in keywords:
        _add(kw, EXPANSION_RULE_KEYWORD, [f"keywords:{kw}"])

    # 2. entities
    for ent in entities:
        _add(ent, EXPANSION_RULE_ENTITY, [f"entities:{ent}"])

    # 3. subquestions — kept as whole phrases, not tokenised
    for sq in profile.subquestions:
        if sq:
            _add(sq, EXPANSION_RULE_SUBQUESTION, [f"subquestions:{sq}"])

    # 4. aliases — analyst-declared synonyms only, e.g. {"DPRK": ["North Korea"]}
    for base_term, synonyms in profile.aliases.items():
        for syn in synonyms:
            _add(syn, EXPANSION_RULE_ALIAS, [f"aliases:{base_term}->{syn}"])

    # 5. keyword x entity
    for kw in keywords:
        for ent in entities:
            _add(f"{kw} {ent}", EXPANSION_RULE_KEYWORD_X_ENTITY, [f"keywords:{kw}", f"entities:{ent}"])

    # 6. keyword x geography
    for kw in keywords:
        for geo in geographies:
            _add(f"{kw} {geo}", EXPANSION_RULE_KEYWORD_X_GEO, [f"keywords:{kw}", f"geographies:{geo}"])

    # 7. entity x geography
    for ent in entities:
        for geo in geographies:
            _add(f"{ent} {geo}", EXPANSION_RULE_ENTITY_X_GEO, [f"entities:{ent}", f"geographies:{geo}"])

    return terms


def base_match_terms(expansion: list[ExpandedTerm]) -> list[ExpandedTerm]:
    """Return only the single-token/single-phrase terms (rules 1-4) — the
    set actually useful for substring matching against harvested text.

    Combination terms (keyword_x_entity etc.) are kept in the dossier for
    transparency about what coverage was *intended*, but matching harvested
    signal text against a two-word combination phrase verbatim is usually
    too strict to be useful; the collector matches on base terms and
    records which base terms hit. STOPWORDS is reused from the existing
    parser so trivial words never become a "matched term" on their own.
    """
    return [
        t for t in expansion
        if t.rule in (EXPANSION_RULE_KEYWORD, EXPANSION_RULE_ENTITY, EXPANSION_RULE_ALIAS, EXPANSION_RULE_SUBQUESTION)
        and t.term not in STOPWORDS
    ]

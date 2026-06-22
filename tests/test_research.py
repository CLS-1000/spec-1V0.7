# @domain:   product
# @module:   test_research
# @loc:      gh_main
# @status:   testing
# @depends:  NONE

"""Tests for cls_research — Research Mode (topic profile, expansion,
collection, dossier assembly, persistence, formatting, full pipeline).

No network calls: collection tests inject pre-built Signal objects via
``collect_for_topic(..., signals=...)`` / ``run_research(..., signals=...)``
instead of hitting the harvester's network path, matching the existing
"external network calls are mocked in all tests" rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from spec1_core.schemas.models import Signal
from spec1_labels import RESEARCH_GAP_MARKER, RESEARCH_STATUS_DRAFT, SOURCE_RSS

from cls_research.schemas import ExpandedTerm, ResearchArtifact, TopicProfile, slugify
from cls_research.expansion import base_match_terms, expand_topic
from cls_research.collector import collect_for_topic, match_terms
from cls_research.dossier import build_dossier
from cls_research.store import DossierStore
from cls_research.topics import list_topic_profiles, load_topic_profile, save_topic_profile
from cls_research.formatter import dossier_to_json, dossier_to_markdown
from cls_research.pipeline import run_research


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def profile() -> TopicProfile:
    return TopicProfile.new(
        name="DPRK Missile Indigenization",
        core_question="Is DPRK reducing reliance on imported missile components?",
        subquestions=[
            "What domestic production capacity exists?",
            "Are sanctions evasion routes still active?",
        ],
        keywords=["missile", "indigenization", "sanctions"],
        entities=["North Korea", "DPRK"],
        geographies=["Korea"],
        aliases={"DPRK": ["North Korea"]},
        exclusions=["sports"],
        time_horizon_days=30,
        source_classes=[SOURCE_RSS, "FARA"],
    )


def _signal(signal_id, source, text, days_ago, url="https://example.com/x"):
    return Signal(
        signal_id=signal_id,
        source=source,
        source_type="rss",
        text=text,
        url=url,
        author="",
        published_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        velocity=0.0,
        engagement=0.0,
        run_id="test-run",
        environment="research",
    )


@pytest.fixture
def signals() -> list[Signal]:
    return [
        _signal("s1", "nk_news", "North Korea unveils new missile indigenization program amid sanctions", 2,
                url="https://nknews.org/a"),
        _signal("s2", "yonhap", "Seoul sports team wins championship", 1, url="https://yna.co.kr/b"),
        _signal("s3", "38_north", "Old missile report from last year", 400, url="https://38north.org/c"),
    ]


# ── TopicProfile ─────────────────────────────────────────────────────────────────

def test_slugify_is_deterministic():
    assert slugify("DPRK Missile Indigenization") == slugify("DPRK Missile Indigenization")
    assert slugify("DPRK Missile Indigenization") == "dprk_missile_indigenization"


def test_topic_profile_make_id_is_deterministic_not_random(profile):
    assert TopicProfile.make_id(profile.name) == profile.topic_id
    assert TopicProfile.make_id(profile.name) == TopicProfile.make_id(profile.name)


def test_topic_profile_to_dict_from_dict_roundtrip(profile):
    d = profile.to_dict()
    restored = TopicProfile.from_dict(d)
    assert restored.topic_id == profile.topic_id
    assert restored.keywords == profile.keywords
    assert restored.aliases == profile.aliases
    assert restored.time_horizon_days == profile.time_horizon_days


# ── Expansion ────────────────────────────────────────────────────────────────────

def test_expand_topic_is_deterministic(profile):
    a = expand_topic(profile)
    b = expand_topic(profile)
    assert [t.to_dict() for t in a] == [t.to_dict() for t in b]


def test_expand_topic_includes_all_rule_types(profile):
    terms = expand_topic(profile)
    rules = {t.rule for t in terms}
    assert "keyword" in rules
    assert "entity" in rules
    assert "alias" in rules
    assert "subquestion" in rules
    assert "keyword_x_entity" in rules
    assert "keyword_x_geography" in rules
    assert "entity_x_geography" in rules


def test_expand_topic_normalizes_case(profile):
    profile.keywords = ["MISSILE"]
    terms = expand_topic(profile)
    keyword_terms = [t.term for t in terms if t.rule == "keyword"]
    assert "missile" in keyword_terms
    assert "MISSILE" not in keyword_terms


def test_expand_topic_dedupes(profile):
    profile.keywords = ["missile", "Missile", "missile "]
    terms = expand_topic(profile)
    keyword_terms = [t.term for t in terms if t.rule == "keyword"]
    assert keyword_terms == ["missile"]


def test_expand_topic_alias_is_analyst_declared_only(profile):
    terms = expand_topic(profile)
    alias_terms = {t.term for t in terms if t.rule == "alias"}
    assert "north korea" in alias_terms
    # No alias was declared for "sanctions" — nothing invented for it.
    assert not any(t.derived_from and "sanctions" in t.derived_from[0] for t in terms if t.rule == "alias")


def test_expand_topic_records_provenance(profile):
    terms = expand_topic(profile)
    kw_x_ent = next(t for t in terms if t.rule == "keyword_x_entity")
    assert any("keywords:" in d for d in kw_x_ent.derived_from)
    assert any("entities:" in d for d in kw_x_ent.derived_from)


def test_base_match_terms_excludes_combinations(profile):
    terms = expand_topic(profile)
    base = base_match_terms(terms)
    assert all(t.rule in ("keyword", "entity", "alias", "subquestion") for t in base)


# ── Collector ────────────────────────────────────────────────────────────────────

def test_collect_for_topic_matches_relevant_signal(profile, signals):
    expansion = expand_topic(profile)
    result = collect_for_topic(profile, expansion, signals=signals)
    assert result.signals_scanned == 3
    matched_signal_ids = {item.signal_id for item in result.items}
    assert "s1" in matched_signal_ids


def test_collect_for_topic_drops_outside_time_horizon(profile, signals):
    expansion = expand_topic(profile)
    result = collect_for_topic(profile, expansion, signals=signals)
    assert result.signals_outside_horizon == 1
    assert "s3" not in {item.signal_id for item in result.items}


def test_collect_for_topic_applies_exclusions(profile, signals):
    expansion = expand_topic(profile)
    result = collect_for_topic(profile, expansion, signals=signals)
    assert result.signals_excluded == 1
    assert "s2" not in {item.signal_id for item in result.items}


def test_collect_for_topic_records_matched_terms_and_rules(profile, signals):
    expansion = expand_topic(profile)
    result = collect_for_topic(profile, expansion, signals=signals)
    item = next(i for i in result.items if i.signal_id == "s1")
    assert "missile" in item.matched_terms
    assert "keyword" in item.matched_rules


def test_collect_for_topic_annotates_credibility_without_filtering(profile, signals):
    expansion = expand_topic(profile)
    result = collect_for_topic(profile, expansion, signals=signals)
    item = next(i for i in result.items if i.signal_id == "s1")
    assert item.credibility_annotation is not None
    assert 0.0 <= item.credibility_annotation <= 1.0


def test_match_terms_is_pure_substring_no_fuzzy_matching():
    terms = [ExpandedTerm(term="missile", rule="keyword")]
    matched, rules = match_terms("a missile launch occurred", terms)
    assert matched == ["missile"]
    matched_none, _ = match_terms("a misile typo occurred", terms)
    assert matched_none == []


# ── Dossier assembly ─────────────────────────────────────────────────────────────

def test_build_dossier_flags_unaddressed_subquestion(profile, signals):
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    artifact = build_dossier(profile, expansion, collection, run_id="r1")
    gap_text = " ".join(artifact.unresolved_questions)
    assert "domestic production capacity" in gap_text
    assert RESEARCH_GAP_MARKER in gap_text


def test_build_dossier_flags_unwired_source_class(profile, signals):
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    artifact = build_dossier(profile, expansion, collection, run_id="r1")
    assert any("FARA" in g for g in artifact.unresolved_questions)


def test_build_dossier_flags_zero_items_as_gap(profile):
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=[])
    artifact = build_dossier(profile, expansion, collection, run_id="r1")
    assert any("no items collected" in g for g in artifact.unresolved_questions)


def test_build_dossier_first_version_has_no_prior(profile, signals):
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    artifact = build_dossier(profile, expansion, collection, run_id="r1", prior=None)
    assert artifact.version == 1
    assert "no prior dossier" in artifact.notable_findings[0]


def test_build_dossier_accumulates_items_across_versions(profile, signals):
    expansion = expand_topic(profile)
    collection_1 = collect_for_topic(profile, expansion, signals=signals)
    v1 = build_dossier(profile, expansion, collection_1, run_id="r1", prior=None)

    new_signal = _signal("s4", "rand", "Fresh missile indigenization analysis", 1)
    collection_2 = collect_for_topic(profile, expansion, signals=signals + [new_signal])
    v2 = build_dossier(profile, expansion, collection_2, run_id="r2", prior=v1)

    assert v2.version == 2
    v2_signal_ids = {it["signal_id"] for it in v2.collected_items}
    assert "s1" in v2_signal_ids  # retained from v1
    assert "s4" in v2_signal_ids  # new in v2
    assert any("1 new item" in f for f in v2.notable_findings)


def test_dossier_id_deterministic_from_topic_and_version():
    assert ResearchArtifact.make_id("topic_x", 3) == "dossier_topic_x_v3"


# ── Store ────────────────────────────────────────────────────────────────────────

def test_dossier_store_save_and_latest(tmp_path, profile, signals):
    store = DossierStore(base_dir=tmp_path / "dossiers")
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    artifact = build_dossier(profile, expansion, collection, run_id="r1")

    store.save(artifact)
    latest = store.latest(profile.topic_id)
    assert latest is not None
    assert latest.dossier_id == artifact.dossier_id
    assert latest.version == 1


def test_dossier_store_latest_picks_highest_version(tmp_path, profile, signals):
    store = DossierStore(base_dir=tmp_path / "dossiers")
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)

    v1 = build_dossier(profile, expansion, collection, run_id="r1")
    store.save(v1)
    v2 = build_dossier(profile, expansion, collection, run_id="r2", prior=v1)
    store.save(v2)

    assert store.latest(profile.topic_id).version == 2
    assert store.count(profile.topic_id) == 2
    assert len(store.history(profile.topic_id)) == 2


def test_dossier_store_latest_returns_none_when_empty(tmp_path):
    store = DossierStore(base_dir=tmp_path / "dossiers")
    assert store.latest("topic_nonexistent") is None


def test_dossier_store_list_topic_ids(tmp_path, profile, signals):
    store = DossierStore(base_dir=tmp_path / "dossiers")
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    store.save(build_dossier(profile, expansion, collection, run_id="r1"))
    assert store.list_topic_ids() == [profile.topic_id]


# ── Topic profile I/O ─────────────────────────────────────────────────────────────

def test_save_and_load_topic_profile_roundtrip(tmp_path, profile):
    path = save_topic_profile(profile, base_dir=tmp_path / "topics")
    loaded = load_topic_profile(path)
    assert loaded.topic_id == profile.topic_id
    assert loaded.core_question == profile.core_question


def test_list_topic_profiles(tmp_path, profile):
    save_topic_profile(profile, base_dir=tmp_path / "topics")
    other = TopicProfile.new(name="Other Topic", core_question="Q?")
    save_topic_profile(other, base_dir=tmp_path / "topics")

    profiles = list_topic_profiles(base_dir=tmp_path / "topics")
    assert {p.topic_id for p in profiles} == {profile.topic_id, other.topic_id}


def test_list_topic_profiles_empty_dir_returns_empty(tmp_path):
    assert list_topic_profiles(base_dir=tmp_path / "nonexistent") == []


# ── Formatter ────────────────────────────────────────────────────────────────────

def test_dossier_to_markdown_separates_required_sections(profile, signals):
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    artifact = build_dossier(profile, expansion, collection, run_id="r1")
    md = dossier_to_markdown(artifact)

    assert "## Topic Definition" in md
    assert "## Notable Findings" in md
    assert "## Unresolved Questions / Collection Gaps" in md
    assert "## Collected Items" in md
    assert "## Provenance" in md


def test_dossier_to_json_matches_to_dict(profile, signals):
    expansion = expand_topic(profile)
    collection = collect_for_topic(profile, expansion, signals=signals)
    artifact = build_dossier(profile, expansion, collection, run_id="r1")
    assert dossier_to_json(artifact) == artifact.to_dict()


# ── Full pipeline ────────────────────────────────────────────────────────────────

def test_run_research_persists_and_writes_markdown(tmp_path, profile, signals):
    store = DossierStore(base_dir=tmp_path / "dossiers")
    artifact = run_research(
        profile,
        signals=signals,
        run_id="r1",
        dossier_store=store,
        markdown_dir=tmp_path / "dossiers",
    )

    assert artifact.status == RESEARCH_STATUS_DRAFT
    assert store.latest(profile.topic_id).dossier_id == artifact.dossier_id

    md_path = tmp_path / "dossiers" / profile.topic_id / "dossier_v1.md"
    latest_path = tmp_path / "dossiers" / profile.topic_id / "dossier_latest.md"
    assert md_path.exists()
    assert latest_path.exists()
    assert latest_path.read_text() == md_path.read_text()


def test_run_research_second_run_increments_version(tmp_path, profile, signals):
    store = DossierStore(base_dir=tmp_path / "dossiers")
    run_research(profile, signals=signals, run_id="r1", dossier_store=store, markdown_dir=tmp_path / "dossiers")
    second = run_research(profile, signals=signals, run_id="r2", dossier_store=store, markdown_dir=tmp_path / "dossiers")

    assert second.version == 2
    assert (tmp_path / "dossiers" / profile.topic_id / "dossier_v2.md").exists()

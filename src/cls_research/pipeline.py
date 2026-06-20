# @domain:   product
# @module:   pipeline
# @loc:      gh_main
# @status:   stable
# @depends:  spec1_core/signal

"""Research Mode pipeline — the analyst-defined-topic counterpart to
``spec1_core.app.cycle`` (the daily Signal Mode cycle).

    topic profile -> expand_topic -> collect_for_topic -> build_dossier
                                                              |
                                                              v
                                            DossierStore (JSONL, append-only)
                                                              |
                                                              v
                                          dossier_to_markdown -> research/dossiers/<topic_id>/

Signal Mode answers "what matters today" across all sources. Research
Mode answers "what do I know about this topic" for one analyst-defined
topic, accumulating across runs. The two share the harvester and parser
(spec1_core.signal) but nothing downstream of that — Research Mode does
not run the 4-gate filter, does not generate investigations, and does not
call an LLM. See docs/research_mode.md for the full comparison.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from spec1_core.core.ids import run_id as new_run_id
from spec1_core.core.logging_utils import get_logger
from spec1_core.schemas.models import Signal

from cls_research.collector import collect_for_topic
from cls_research.dossier import build_dossier
from cls_research.expansion import expand_topic
from cls_research.formatter import dossier_to_markdown
from cls_research.schemas import ResearchArtifact, TopicProfile
from cls_research.store import DEFAULT_DOSSIERS_DIR, DossierStore

logger = get_logger(__name__)

DEFAULT_DOSSIER_MD_DIR = DEFAULT_DOSSIERS_DIR


def _write_markdown(artifact: ResearchArtifact, md_dir: Path) -> Path:
    topic_dir = md_dir / artifact.topic_id
    topic_dir.mkdir(parents=True, exist_ok=True)
    versioned_path = topic_dir / f"dossier_v{artifact.version}.md"
    latest_path = topic_dir / "dossier_latest.md"
    rendered = dossier_to_markdown(artifact)
    for path in (versioned_path, latest_path):
        with path.open("w", encoding="utf-8") as fh:
            fh.write(rendered)
    return versioned_path


def run_research(
    profile: TopicProfile,
    feeds: Optional[dict[str, str]] = None,
    signals: Optional[list[Signal]] = None,
    run_id: Optional[str] = None,
    environment: str = "research",
    dossier_store: Optional[DossierStore] = None,
    markdown_dir: Optional[Path] = None,
) -> ResearchArtifact:
    """Run one Research Mode pass for a topic and persist the resulting dossier.

    Args:
        profile: the topic to research.
        feeds: optional feed override (defaults to the standard Signal Mode
            feed set). Ignored if ``signals`` is given.
        signals: optional pre-harvested signals to reuse instead of making
            a fresh network call — e.g. the batch a Signal Mode cycle just
            harvested in the same run.
        run_id: optional run id; a new one is generated if omitted.
        environment: tag applied to freshly-harvested signals.
        dossier_store: optional DossierStore override (default: JSONL under
            research/dossiers/).
        markdown_dir: optional override for where the human-readable
            Markdown rendering is written (default: same research/dossiers/
            tree, alongside the JSONL store).

    Returns:
        The newly created ResearchArtifact (already persisted).
    """
    run_id = run_id or new_run_id()
    store = dossier_store or DossierStore()

    prior = store.latest(profile.topic_id)

    expansion = expand_topic(profile)
    collection = collect_for_topic(
        profile,
        expansion,
        feeds=feeds,
        signals=signals,
        run_id=run_id,
        environment=environment,
    )
    artifact = build_dossier(profile, expansion, collection, run_id=run_id, prior=prior)

    store.save(artifact)
    md_path = _write_markdown(artifact, markdown_dir or DEFAULT_DOSSIER_MD_DIR)

    logger.info(
        f"research_run_complete: topic_id={profile.topic_id}, version={artifact.version}, "
        f"items={len(artifact.collected_items)}, gaps={len(artifact.unresolved_questions)}, "
        f"markdown={md_path}"
    )

    return artifact

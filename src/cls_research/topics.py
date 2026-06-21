# @domain:   product
# @module:   topics
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Topic profile I/O — analyst-authored JSON files under research/topics/.

Topic profiles are inputs, not generated records, so they live as plain
JSON files (one per topic, named by topic_id) rather than an append-only
JSONL log — an analyst edits a topic profile in place as a research
question evolves, the same way ``workspace/cases/case_*.json`` is a single
file per case rather than a log of every edit.
"""

from __future__ import annotations

import json
from pathlib import Path

from cls_research.schemas import TopicProfile

DEFAULT_TOPICS_DIR = Path("research/topics")


def topic_profile_path(topic_id: str, base_dir: Path = DEFAULT_TOPICS_DIR) -> Path:
    return Path(base_dir) / f"{topic_id}.json"


def save_topic_profile(profile: TopicProfile, base_dir: Path = DEFAULT_TOPICS_DIR) -> Path:
    """Write a TopicProfile to research/topics/<topic_id>.json. Overwrites in place."""
    path = topic_profile_path(profile.topic_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(profile.to_dict(), fh, indent=2, default=str)
        fh.write("\n")
    return path


def load_topic_profile(path: Path) -> TopicProfile:
    """Read a single topic profile JSON file by path."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        return TopicProfile.from_dict(json.load(fh))


def load_topic_profile_by_id(topic_id: str, base_dir: Path = DEFAULT_TOPICS_DIR) -> TopicProfile:
    """Read a topic profile by its topic_id from the default topics directory."""
    return load_topic_profile(topic_profile_path(topic_id, base_dir))


def list_topic_profiles(base_dir: Path = DEFAULT_TOPICS_DIR) -> list[TopicProfile]:
    """Load every topic profile JSON file in a directory."""
    base_dir = Path(base_dir)
    if not base_dir.exists():
        return []
    profiles = []
    for path in sorted(base_dir.glob("*.json")):
        try:
            profiles.append(load_topic_profile(path))
        except (json.JSONDecodeError, KeyError):
            continue
    return profiles

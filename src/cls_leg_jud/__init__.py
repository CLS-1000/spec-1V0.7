"""Legislative & Judicial Desk — rule-based brief synthesis."""
from cls_leg_jud.producer import produce_brief
from cls_leg_jud.schemas import LegJudBrief, LegJudSection, SECTION_TITLES
from cls_leg_jud.store import LegJudStore
from cls_leg_jud.formatter import to_markdown, section_to_markdown, to_json_summary

__all__ = [
    "produce_brief",
    "LegJudBrief",
    "LegJudSection",
    "SECTION_TITLES",
    "LegJudStore",
    "to_markdown",
    "section_to_markdown",
    "to_json_summary",
]

"""Investigation workspace for persistent case files."""

from spec1_core.workspace.case import (
    open_case,
    update_case,
    close_case,
    list_cases,
    get_case,
)
from spec1_core.workspace.tracker import match_signals_to_cases
from spec1_core.workspace.researcher import run_research

__all__ = [
    "open_case",
    "update_case",
    "close_case",
    "list_cases",
    "get_case",
    "match_signals_to_cases",
    "run_research",
]

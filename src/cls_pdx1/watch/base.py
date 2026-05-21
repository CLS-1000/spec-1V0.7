"""Abstract base and registry for watch modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from cls_pdx1.models import Signal


@dataclass
class WatchResult:
    entity_id: str
    entity_name: str
    signals: list[Signal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return len(self.errors) == 0


class WatchModule(ABC):
    entity_id: str = ""
    entity_name: str = ""

    @abstractmethod
    def collect(self) -> WatchResult:
        """Collect signals for this entity. Must not raise."""
        ...


# Registry of all watch module classes indexed by entity_id
WATCH_REGISTRY: dict[str, type[WatchModule]] = {}


def register_watch(cls: type[WatchModule]) -> type[WatchModule]:
    WATCH_REGISTRY[cls.entity_id] = cls
    return cls

"""Adapter base class and registry for the SPEC-1 custom adapter marketplace.

Every custom signal adapter must subclass :class:`AdapterBase` and register
itself via :func:`register_adapter`.  Built-in adapters (RSS, FARA, Congress,
Narrative) are pre-registered on import.

Example — minimal custom adapter::

    from cls_osint.adapters.registry import AdapterBase, register_adapter
    from cls_osint.schemas import OSINTRecord

    class MyRSSAdapter(AdapterBase):
        name = "my_source"
        source_type = "RSS"
        description = "Custom feed from MySource.io"
        version = "1.0.0"
        author = "Jane Doe"
        tags = ["finance", "markets"]

        def fetch(self) -> list[OSINTRecord]:
            ...

    register_adapter(MyRSSAdapter)
"""

from __future__ import annotations

import abc
import threading
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional, Type

from cls_osint.schemas import OSINTRecord


# ── Adapter base class ─────────────────────────────────────────────────────────

class AdapterBase(abc.ABC):
    """Abstract base class for SPEC-1 signal adapters.

    Subclasses MUST define the class-level attributes and implement
    :meth:`fetch`.
    """

    #: Unique machine-readable name (snake_case, lowercase)
    name: ClassVar[str]
    #: Source type string (e.g. "RSS", "FARA", "CONGRESSIONAL", "NARRATIVE", "CUSTOM")
    source_type: ClassVar[str] = "CUSTOM"
    #: Human-readable description of the data source
    description: ClassVar[str] = ""
    #: Semantic version of the adapter
    version: ClassVar[str] = "0.1.0"
    #: Author/maintainer string
    author: ClassVar[str] = ""
    #: Taxonomy tags for discovery
    tags: ClassVar[list[str]] = []
    #: Whether the adapter is active by default
    active: ClassVar[bool] = True

    @abc.abstractmethod
    def fetch(self) -> list[OSINTRecord]:
        """Collect and return a list of :class:`~cls_osint.schemas.OSINTRecord`."""

    def validate(self) -> list[str]:
        """Return a list of validation error strings (empty = valid)."""
        errors: list[str] = []
        for attr in ("name", "source_type", "description"):
            if not getattr(self.__class__, attr, ""):
                errors.append(f"class attribute '{attr}' must be non-empty")
        return errors

    @classmethod
    def metadata(cls) -> dict:
        """Return adapter metadata as a plain dict."""
        return {
            "name": cls.name,
            "source_type": cls.source_type,
            "description": cls.description,
            "version": cls.version,
            "author": cls.author,
            "tags": list(cls.tags),
            "active": cls.active,
        }


# ── Registry ───────────────────────────────────────────────────────────────────

@dataclass
class AdapterInfo:
    """Lightweight descriptor stored in the registry."""

    name: str
    source_type: str
    description: str
    version: str
    author: str
    tags: list[str]
    active: bool
    cls: Type[AdapterBase]


_registry_lock = threading.Lock()
_registry: Dict[str, AdapterInfo] = {}


def register_adapter(adapter_cls: Type[AdapterBase]) -> None:
    """Register an adapter class.

    Raises :exc:`ValueError` if the class lacks a ``name`` attribute or if
    another adapter with the same name is already registered.
    """
    name = getattr(adapter_cls, "name", None)
    if not name:
        raise ValueError(f"Adapter class {adapter_cls!r} must define a non-empty 'name' class attribute")

    with _registry_lock:
        if name in _registry:
            raise ValueError(f"Adapter '{name}' is already registered")
        _registry[name] = AdapterInfo(
            name=name,
            source_type=getattr(adapter_cls, "source_type", "CUSTOM"),
            description=getattr(adapter_cls, "description", ""),
            version=getattr(adapter_cls, "version", "0.1.0"),
            author=getattr(adapter_cls, "author", ""),
            tags=list(getattr(adapter_cls, "tags", [])),
            active=getattr(adapter_cls, "active", True),
            cls=adapter_cls,
        )


def unregister_adapter(name: str) -> bool:
    """Remove an adapter from the registry.  Returns True if it was present."""
    with _registry_lock:
        return _registry.pop(name, None) is not None


def get_adapter(name: str) -> Optional[AdapterInfo]:
    """Return :class:`AdapterInfo` for *name*, or ``None`` if not found."""
    with _registry_lock:
        return _registry.get(name)


def list_adapters(
    source_type: Optional[str] = None,
    active_only: bool = False,
) -> List[AdapterInfo]:
    """Return a list of registered adapters, optionally filtered."""
    with _registry_lock:
        items = list(_registry.values())
    if source_type:
        items = [a for a in items if a.source_type.upper() == source_type.upper()]
    if active_only:
        items = [a for a in items if a.active]
    return items


def adapter_count() -> int:
    """Return the total number of registered adapters."""
    with _registry_lock:
        return len(_registry)


# ── Built-in adapter stubs ─────────────────────────────────────────────────────
# These represent the adapters already present in cls_osint.  They are
# pre-registered so the marketplace endpoint reflects the full picture.

class _RSSAdapter(AdapterBase):
    name = "rss"
    source_type = "RSS"
    description = "Generic RSS/Atom feed adapter (feedparser + httpx)"
    version = "1.0.0"
    author = "SPEC-1 core"
    tags = ["rss", "news", "feeds"]

    def fetch(self) -> list[OSINTRecord]:  # pragma: no cover — integration; covered by tests/test_feed.py
        from cls_osint.feed import fetch_all_rss
        from cls_osint.sources import get_sources_by_type
        result = fetch_all_rss(get_sources_by_type("RSS"))
        return result["records"]


class _FARAAdapter(AdapterBase):
    name = "fara"
    source_type = "FARA"
    description = "FARA (Foreign Agents Registration Act) filings adapter"
    version = "1.0.0"
    author = "SPEC-1 core"
    tags = ["fara", "foreign_agents", "lobbying", "government"]

    def fetch(self) -> list[OSINTRecord]:  # pragma: no cover — integration; covered by tests/test_fara.py
        from cls_osint.adapters.fara import fetch_fara_records
        return list(fetch_fara_records())


class _CongressionalAdapter(AdapterBase):
    name = "congressional"
    source_type = "CONGRESSIONAL"
    description = "Congressional bills and legislation adapter"
    version = "1.0.0"
    author = "SPEC-1 core"
    tags = ["congress", "legislation", "bills", "government"]

    def fetch(self) -> list[OSINTRecord]:  # pragma: no cover — integration; covered by tests/test_congressional.py
        from cls_osint.adapters.congressional import fetch_congressional_records
        return list(fetch_congressional_records())


class _NarrativeAdapter(AdapterBase):
    name = "narrative"
    source_type = "NARRATIVE"
    description = "Narrative tracking and influence operation detection adapter"
    version = "1.0.0"
    author = "SPEC-1 core"
    tags = ["narrative", "influence", "psyop"]

    def fetch(self) -> list[OSINTRecord]:  # pragma: no cover — integration; covered by tests/test_narrative.py
        from cls_osint.adapters.narrative import fetch_narrative_records
        return list(fetch_narrative_records())


# Register built-in adapters on module import
for _cls in (_RSSAdapter, _FARAAdapter, _CongressionalAdapter, _NarrativeAdapter):
    register_adapter(_cls)

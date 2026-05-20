"""Tests for cls_osint.adapters.registry — adapter marketplace registry."""

from __future__ import annotations

import pytest

from cls_osint.schemas import OSINTRecord


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_adapter_cls(name="test_adapter", source_type="CUSTOM", desc="A test adapter"):
    """Dynamically create a minimal AdapterBase subclass for testing."""
    from cls_osint.adapters.registry import AdapterBase

    class _TestAdapter(AdapterBase):
        def fetch(self) -> list[OSINTRecord]:
            return []

    _TestAdapter.name = name
    _TestAdapter.source_type = source_type
    _TestAdapter.description = desc
    _TestAdapter.version = "0.1.0"
    _TestAdapter.author = "Tester"
    _TestAdapter.tags = ["test"]
    _TestAdapter.active = True
    return _TestAdapter


@pytest.fixture(autouse=True)
def clean_registry():
    """Remove any test adapters after each test."""
    from cls_osint.adapters import registry as reg
    # Remember adapters before the test
    before = set(reg._registry.keys())
    yield
    # Remove anything added by the test
    with reg._registry_lock:
        for k in list(reg._registry.keys()):
            if k not in before:
                del reg._registry[k]


# ── register_adapter ───────────────────────────────────────────────────────────

class TestRegisterAdapter:
    def test_registers_new_adapter(self):
        from cls_osint.adapters.registry import register_adapter, get_adapter
        cls = _make_adapter_cls("my_adapter")
        register_adapter(cls)
        assert get_adapter("my_adapter") is not None

    def test_duplicate_raises_value_error(self):
        from cls_osint.adapters.registry import register_adapter
        cls = _make_adapter_cls("dup_adapter")
        register_adapter(cls)
        with pytest.raises(ValueError, match="already registered"):
            register_adapter(cls)

    def test_missing_name_raises_value_error(self):
        from cls_osint.adapters.registry import AdapterBase, register_adapter

        class _NoName(AdapterBase):
            def fetch(self):
                return []

        with pytest.raises(ValueError, match="name"):
            register_adapter(_NoName)

    def test_adapter_info_has_correct_fields(self):
        from cls_osint.adapters.registry import register_adapter, get_adapter
        cls = _make_adapter_cls("field_check", source_type="RSS", desc="Field check")
        register_adapter(cls)
        info = get_adapter("field_check")
        assert info.name == "field_check"
        assert info.source_type == "RSS"
        assert info.description == "Field check"
        assert info.version == "0.1.0"
        assert info.author == "Tester"
        assert info.active is True


# ── unregister_adapter ─────────────────────────────────────────────────────────

class TestUnregisterAdapter:
    def test_unregisters_existing(self):
        from cls_osint.adapters.registry import register_adapter, unregister_adapter, get_adapter
        cls = _make_adapter_cls("to_remove")
        register_adapter(cls)
        assert unregister_adapter("to_remove") is True
        assert get_adapter("to_remove") is None

    def test_returns_false_for_missing(self):
        from cls_osint.adapters.registry import unregister_adapter
        assert unregister_adapter("does_not_exist_xyz") is False


# ── list_adapters ──────────────────────────────────────────────────────────────

class TestListAdapters:
    def test_returns_all_including_builtins(self):
        from cls_osint.adapters.registry import list_adapters
        adapters = list_adapters()
        names = [a.name for a in adapters]
        assert "rss" in names
        assert "fara" in names
        assert "congressional" in names
        assert "narrative" in names

    def test_filter_by_source_type(self):
        from cls_osint.adapters.registry import list_adapters
        rss_adapters = list_adapters(source_type="RSS")
        assert all(a.source_type == "RSS" for a in rss_adapters)
        assert len(rss_adapters) >= 1

    def test_filter_active_only(self):
        from cls_osint.adapters.registry import register_adapter, list_adapters, AdapterBase

        class _InactiveAdapter(AdapterBase):
            name = "inactive_test"
            source_type = "CUSTOM"
            description = "inactive"
            active = False

            def fetch(self):
                return []

        register_adapter(_InactiveAdapter)
        active = list_adapters(active_only=True)
        assert all(a.active for a in active)

    def test_custom_adapter_appears_in_list(self):
        from cls_osint.adapters.registry import register_adapter, list_adapters
        cls = _make_adapter_cls("visible_adapter")
        register_adapter(cls)
        names = [a.name for a in list_adapters()]
        assert "visible_adapter" in names

    def test_case_insensitive_source_type_filter(self):
        from cls_osint.adapters.registry import list_adapters
        lower = list_adapters(source_type="rss")
        upper = list_adapters(source_type="RSS")
        assert len(lower) == len(upper)


# ── adapter_count ──────────────────────────────────────────────────────────────

class TestAdapterCount:
    def test_count_includes_builtins(self):
        from cls_osint.adapters.registry import adapter_count
        assert adapter_count() >= 4  # rss, fara, congressional, narrative

    def test_count_increases_on_register(self):
        from cls_osint.adapters.registry import register_adapter, adapter_count
        before = adapter_count()
        cls = _make_adapter_cls("count_test")
        register_adapter(cls)
        assert adapter_count() == before + 1


# ── AdapterBase.validate ───────────────────────────────────────────────────────

class TestAdapterBaseValidate:
    def test_valid_adapter_has_no_errors(self):
        cls = _make_adapter_cls("valid_adapter")
        instance = cls()
        assert instance.validate() == []

    def test_missing_description_returns_error(self):
        cls = _make_adapter_cls("nodesc_adapter", desc="")
        instance = cls()
        errors = instance.validate()
        assert any("description" in e for e in errors)

    def test_metadata_returns_dict(self):
        cls = _make_adapter_cls("meta_adapter")
        meta = cls.metadata()
        assert meta["name"] == "meta_adapter"
        assert "source_type" in meta
        assert "tags" in meta


# ── Built-in adapters ──────────────────────────────────────────────────────────

class TestBuiltinAdapters:
    def test_rss_adapter_registered(self):
        from cls_osint.adapters.registry import get_adapter
        info = get_adapter("rss")
        assert info is not None
        assert info.source_type == "RSS"

    def test_fara_adapter_registered(self):
        from cls_osint.adapters.registry import get_adapter
        info = get_adapter("fara")
        assert info is not None
        assert "fara" in info.tags

    def test_congressional_adapter_registered(self):
        from cls_osint.adapters.registry import get_adapter
        info = get_adapter("congressional")
        assert info is not None
        assert "congress" in info.tags

    def test_narrative_adapter_registered(self):
        from cls_osint.adapters.registry import get_adapter
        info = get_adapter("narrative")
        assert info is not None
        assert "narrative" in info.tags

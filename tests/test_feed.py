"""Tests for cls_osint.feed — RSS feed fetching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cls_osint.schemas import OSINTRecord
from cls_osint.sources import OsintSource


def _make_source(name="test_source", url="https://example.com/feed"):
    return OsintSource(
        name=name,
        source_type="RSS",
        url=url,
        credibility=0.8,
        tags=["test"],
    )


def _make_entry(title="Test Article", link="https://example.com/article-1", summary="Some summary"):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.description = summary
    entry.content = []
    entry.author = "Test Author"
    entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 15, 0)
    entry.updated_parsed = None
    return entry


def _make_feed(entries=None, bozo=False):
    feed = MagicMock()
    feed.entries = entries or []
    feed.bozo = bozo
    feed.bozo_exception = None
    feed.get = lambda k, d=None: getattr(feed, k, d)
    return feed


class TestFetchFeed:
    def test_yields_osint_records(self):
        from cls_osint.feed import fetch_feed

        entry = _make_entry()
        mock_parsed = _make_feed(entries=[entry])

        source = _make_source()
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            records = list(fetch_feed(source))

        assert len(records) == 1
        assert isinstance(records[0], OSINTRecord)
        assert records[0].source_name == "test_source"
        assert records[0].source_type == "RSS"
        assert "Test Article" in records[0].content

    def test_skips_entries_without_title(self):
        from cls_osint.feed import fetch_feed

        entry_no_title = _make_entry(title="", link="https://example.com/x")
        entry_ok = _make_entry(title="Good Article", link="https://example.com/y")
        mock_parsed = _make_feed(entries=[entry_no_title, entry_ok])

        source = _make_source()
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            records = list(fetch_feed(source))

        assert len(records) == 1
        assert "Good Article" in records[0].content

    def test_skips_entries_without_link(self):
        from cls_osint.feed import fetch_feed

        entry_no_link = _make_entry(title="No Link Article", link="")
        mock_parsed = _make_feed(entries=[entry_no_link])

        source = _make_source()
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            records = list(fetch_feed(source))

        assert len(records) == 0

    def test_raises_on_bozo_with_no_entries(self):
        from cls_osint.feed import fetch_feed

        mock_parsed = _make_feed(entries=[], bozo=True)
        mock_parsed.bozo_exception = Exception("Bad XML")
        mock_parsed.get = lambda k, d=None: {
            "entries": [],
            "bozo": True,
            "bozo_exception": Exception("Bad XML"),
        }.get(k, d)

        source = _make_source()
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            with pytest.raises(RuntimeError):
                list(fetch_feed(source))

    def test_record_id_is_deterministic(self):
        from cls_osint.feed import fetch_feed

        entry = _make_entry(title="Same Title", link="https://example.com/same")
        mock_parsed = _make_feed(entries=[entry])

        source = _make_source()
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            records1 = list(fetch_feed(source))
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            records2 = list(fetch_feed(source))

        assert records1[0].record_id == records2[0].record_id

    def test_metadata_includes_tags(self):
        from cls_osint.feed import fetch_feed

        entry = _make_entry()
        mock_parsed = _make_feed(entries=[entry])
        source = _make_source(name="rand")
        source.tags = ["policy", "defense"]

        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            records = list(fetch_feed(source))

        assert "tags" in records[0].metadata
        assert "policy" in records[0].metadata["tags"]

    def test_network_failure_retries(self):
        from cls_osint.feed import fetch_feed

        source = _make_source()
        fail_count = 0

        def flaky_parse(name, url, timeout):
            nonlocal fail_count
            fail_count += 1
            if fail_count < 2:
                raise ConnectionError("temporary failure")
            return _make_feed(entries=[_make_entry()])

        with patch("cls_osint.feed._parse_feed", side_effect=flaky_parse):
            with patch("cls_osint.feed.time.sleep"):
                records = list(fetch_feed(source, max_retries=2))

        assert len(records) == 1
        assert fail_count == 2

    def test_exhausted_retries_raises(self):
        from cls_osint.feed import fetch_feed

        source = _make_source()
        with patch("cls_osint.feed._parse_feed", side_effect=ConnectionError("always fails")):
            with patch("cls_osint.feed.time.sleep"):
                with pytest.raises(RuntimeError):
                    list(fetch_feed(source, max_retries=1))


class TestFetchAllRss:
    def test_aggregates_multiple_sources(self):
        from cls_osint.feed import fetch_all_rss

        entry = _make_entry()
        mock_parsed = _make_feed(entries=[entry])

        sources = [_make_source("src1"), _make_source("src2")]
        with patch("cls_osint.feed._parse_feed", return_value=mock_parsed):
            result = fetch_all_rss(sources)

        assert len(result["records"]) == 2
        assert result["errors"] == {}

    def test_captures_per_source_errors(self):
        from cls_osint.feed import fetch_all_rss

        sources = [_make_source("good"), _make_source("bad")]

        def flaky(name, url, timeout):
            if name == "bad":
                raise RuntimeError("bad feed")
            return _make_feed(entries=[_make_entry()])

        with patch("cls_osint.feed._parse_feed", side_effect=flaky):
            with patch("cls_osint.feed.time.sleep"):
                result = fetch_all_rss(sources)

        assert len(result["records"]) == 1
        assert "bad" in result["errors"]

    def test_empty_sources_returns_empty(self):
        from cls_osint.feed import fetch_all_rss

        result = fetch_all_rss([])
        assert result["records"] == []
        assert result["errors"] == {}


# ── Async feed fetching ────────────────────────────────────────────────────────

def _make_feed_xml(title="Test", link="https://example.com/art", summary="Body"):
    return f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{summary}</description>
    </item>
  </channel>
</rss>"""


def _make_ok_async_client_cls(xml: str):
    """Return a fake httpx.AsyncClient class that always returns *xml*."""
    class _OkAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, **kw):
            resp = MagicMock()
            resp.text = xml
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            return resp

    return _OkAsyncClient


def _make_fail_async_client_cls(exc=None):
    """Return a fake httpx.AsyncClient class that always raises *exc*."""
    if exc is None:
        exc = RuntimeError("simulated network error")

    class _FailAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, **kw):
            raise exc

    return _FailAsyncClient


class TestFetchAllRssAsync:
    """Tests for fetch_all_rss_async — concurrent httpx-based fetching."""

    def test_empty_sources_returns_empty(self):
        import asyncio
        from cls_osint.feed import fetch_all_rss_async

        result = asyncio.run(fetch_all_rss_async([]))
        assert result["records"] == []
        assert result["errors"] == {}

    def test_returns_records_from_feeds(self):
        import asyncio
        from cls_osint.feed import fetch_all_rss_async

        xml = _make_feed_xml()
        source = _make_source("async_src")

        with patch("httpx.AsyncClient", _make_ok_async_client_cls(xml)):
            result = asyncio.run(fetch_all_rss_async([source]))

        assert len(result["records"]) >= 1
        assert result["errors"] == {}

    def test_per_source_errors_captured(self):
        import asyncio
        from cls_osint.feed import fetch_all_rss_async

        source = _make_source("err_src")

        with patch("httpx.AsyncClient", _make_fail_async_client_cls()):
            result = asyncio.run(fetch_all_rss_async([source], max_retries=0))

        assert "err_src" in result["errors"]

    def test_concurrent_multiple_sources(self):
        import asyncio
        from cls_osint.feed import fetch_all_rss_async

        xml = _make_feed_xml()
        sources = [_make_source(f"async_src_{i}", f"https://example.com/feed{i}") for i in range(3)]

        with patch("httpx.AsyncClient", _make_ok_async_client_cls(xml)):
            result = asyncio.run(fetch_all_rss_async(sources))
        assert len(result["records"]) == 3
        assert result["errors"] == {}

    def test_returns_same_structure_as_sync(self):
        """fetch_all_rss_async returns a dict with 'records' and 'errors' keys."""
        import asyncio
        from cls_osint.feed import fetch_all_rss_async

        result = asyncio.run(fetch_all_rss_async([]))
        assert isinstance(result, dict)
        assert "records" in result
        assert "errors" in result
        assert isinstance(result["records"], list)
        assert isinstance(result["errors"], dict)

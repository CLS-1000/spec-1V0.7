# @domain:   intelligence
# @module:   feed
# @loc:      gh_main
# @status:   stable
# @depends:  cls_db, spec1_core

"""Generic feed fetcher used across cls_osint adapters.

Wraps feedparser with retry logic and source-specific workarounds.
Also provides an async variant (fetch_all_rss_async) using httpx for
concurrent multi-source fetching (2-3x faster on large source lists).
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from typing import Iterator

import feedparser
import requests

from cls_osint.schemas import OSINTRecord
from cls_osint.sources import OsintSource, get_credibility

TIMEOUT = 15
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
_SPEC1_HEADERS = {"User-Agent": "spec1-engine/0.3"}
_SSL_UNVERIFIED: set[str] = {"cipher_brief"}
_ILLEGAL_XML_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff\ufffe\uffff]"
)


def _make_record_id(url: str, title: str) -> str:
    raw = f"{url}::{title}"
    return "osint_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def _parse_date(entry: feedparser.FeedParserDict) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def _get_text(entry: feedparser.FeedParserDict) -> str:
    parts: list[str] = []
    if hasattr(entry, "title") and entry.title:
        parts.append(str(entry.title))
    if hasattr(entry, "summary") and entry.summary:
        parts.append(str(entry.summary))
    elif hasattr(entry, "description") and entry.description:
        parts.append(str(entry.description))
    return " ".join(parts)


def _fetch_raw_no_ssl(url: str, timeout: int) -> bytes:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=_SPEC1_HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read()


def _fetch_raw_sanitized(url: str, timeout: int) -> bytes:
    resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=timeout, verify=True)
    resp.raise_for_status()
    text = _ILLEGAL_XML_RE.sub("", resp.text)
    return text.encode("utf-8")


def _parse_feed(name: str, url: str, timeout: int) -> feedparser.FeedParserDict:
    if name in _SSL_UNVERIFIED:
        raw = _fetch_raw_no_ssl(url, timeout)
        return feedparser.parse(raw)
    return feedparser.parse(url, request_headers=_SPEC1_HEADERS)


def fetch_feed(
    source: OsintSource,
    timeout: int = TIMEOUT,
    max_retries: int = 2,
) -> Iterator[OSINTRecord]:
    """Fetch a single RSS feed and yield OSINTRecord instances.

    Retries up to max_retries times on network failure.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            parsed = _parse_feed(source.name, source.url, timeout)
            break
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"Failed to fetch {source.name} after {max_retries} retries: {last_exc}")

    if parsed.get("bozo") and not parsed.get("entries"):
        exc = parsed.get("bozo_exception")
        raise RuntimeError(f"Feed parse error for {source.name}: {exc}")

    for entry in parsed.get("entries", []):
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""
        if not title or not link:
            continue

        text = _get_text(entry)
        published_at = _parse_date(entry)
        record_id = _make_record_id(link, title)

        yield OSINTRecord(
            record_id=record_id,
            source_type="RSS",
            source_name=source.name,
            content=text,
            url=link,
            collected_at=published_at,
            metadata={
                "feed_url": source.url,
                "tags": source.tags,
                "credibility": get_credibility(source.name),
            },
        )


def fetch_all_rss(
    sources: list[OsintSource],
    timeout: int = TIMEOUT,
) -> dict:
    """Fetch multiple RSS feeds; return records and any per-source errors."""
    records: list[OSINTRecord] = []
    errors: dict[str, str] = {}

    for source in sources:
        try:
            batch = list(fetch_feed(source, timeout=timeout))
            records.extend(batch)
        except Exception as exc:
            errors[source.name] = str(exc)

    return {"records": records, "errors": errors}


# ── Async feed fetching ────────────────────────────────────────────────────────

async def _fetch_feed_bytes_async(
    source: OsintSource,
    timeout: int,
    max_retries: int,
) -> tuple[OsintSource, bytes | None, str | None]:
    """Fetch raw feed bytes asynchronously using httpx.

    Returns (source, raw_bytes, error_string).  error_string is None on success.
    """
    try:
        import httpx
    except ImportError:
        # Graceful fallback: run synchronous fetch in thread executor
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, lambda: list(fetch_feed(source, timeout=timeout, max_retries=max_retries))
            )
            return source, None, None  # sentinel; caller will handle sync fallback
        except Exception as exc:
            return source, None, str(exc)

    headers = dict(_BROWSER_HEADERS)
    if source.name in _SSL_UNVERIFIED:
        headers = dict(_SPEC1_HEADERS)

    last_exc: str | None = None
    for attempt in range(max_retries + 1):
        try:
            verify = source.name not in _SSL_UNVERIFIED
            async with httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                verify=verify,
                follow_redirects=True,
            ) as client:
                resp = await client.get(source.url)
                resp.raise_for_status()
                raw = _ILLEGAL_XML_RE.sub("", resp.text).encode("utf-8")
                return source, raw, None
        except Exception as exc:
            last_exc = str(exc)
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)

    return source, None, f"Failed after {max_retries} retries: {last_exc}"


def _parse_records_from_bytes(source: OsintSource, raw: bytes) -> list[OSINTRecord]:
    """Parse raw feed bytes into OSINTRecord list."""
    parsed = feedparser.parse(raw)
    if parsed.get("bozo") and not parsed.get("entries"):
        exc = parsed.get("bozo_exception")
        raise RuntimeError(f"Feed parse error for {source.name}: {exc}")

    records: list[OSINTRecord] = []
    for entry in parsed.get("entries", []):
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""
        if not title or not link:
            continue
        text = _get_text(entry)
        published_at = _parse_date(entry)
        record_id = _make_record_id(link, title)
        records.append(
            OSINTRecord(
                record_id=record_id,
                source_type="RSS",
                source_name=source.name,
                content=text,
                url=link,
                collected_at=published_at,
                metadata={
                    "feed_url": source.url,
                    "tags": source.tags,
                    "credibility": get_credibility(source.name),
                },
            )
        )
    return records


async def fetch_all_rss_async(
    sources: list[OsintSource],
    timeout: int = TIMEOUT,
    max_retries: int = 2,
    max_concurrent: int = 10,
) -> dict:
    """Fetch multiple RSS feeds concurrently using httpx.

    Runs up to *max_concurrent* requests simultaneously (semaphore-limited)
    which gives 2-3x speedup on typical multi-source workloads vs the serial
    :func:`fetch_all_rss`.

    Returns the same ``{"records": [...], "errors": {...}}`` dict as
    :func:`fetch_all_rss` for full backward compatibility.

    Falls back gracefully to :func:`fetch_all_rss` if httpx is unavailable.
    """
    try:
        import httpx as _httpx  # noqa: F401 — just test importability
    except ImportError:
        # httpx not installed — fall back to sync implementation
        return fetch_all_rss(sources, timeout=timeout)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _guarded_fetch(src: OsintSource):
        async with semaphore:
            return await _fetch_feed_bytes_async(src, timeout, max_retries)

    results = await asyncio.gather(*[_guarded_fetch(s) for s in sources])

    records: list[OSINTRecord] = []
    errors: dict[str, str] = {}

    def _sync_fetch(src: OsintSource) -> list[OSINTRecord]:
        return list(fetch_feed(src, timeout=timeout, max_retries=max_retries))

    for source, raw, error in results:
        if error is not None:
            errors[source.name] = error
        elif raw is None:
            # httpx unavailable sentinel — run sync in executor
            loop = asyncio.get_event_loop()
            try:
                import functools
                batch = await loop.run_in_executor(
                    None, functools.partial(_sync_fetch, source)
                )
                records.extend(batch)
            except Exception as exc:
                errors[source.name] = str(exc)
        else:
            try:
                records.extend(_parse_records_from_bytes(source, raw))
            except Exception as exc:
                errors[source.name] = str(exc)

    return {"records": records, "errors": errors}

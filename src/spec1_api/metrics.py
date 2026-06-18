# @domain:   machine
# @module:   metrics
# @loc:      gh_main
# @status:   stable
# @depends:  spec1_core, cls_db

"""Thread-safe in-process metrics collector for SPEC-1 API.

Tracks:
- API request counts and latency histograms (per endpoint)
- Cycle stats (duration, signal/record throughput, error counts)
- Store sizes (intel, leads, psyop, verdicts)

Expose via GET /metrics (Prometheus text format) and GET /metrics/json.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

# ── Internal state ─────────────────────────────────────────────────────────────

_lock = threading.Lock()

# request_counts[method][path] -> int
_request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

# request_errors[method][path] -> int  (status >= 400)
_request_errors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

# latency_buckets[method][path] -> list[float] (seconds, capped at last 10 000)
_MAX_LATENCY_SAMPLES = 10_000
_latency_samples: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))


@dataclass
class CycleStats:
    run_id: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    duration_seconds: float = 0.0
    signals_harvested: int = 0
    records_stored: int = 0
    errors: int = 0
    success: bool = True


_cycle_history: List[CycleStats] = []
_MAX_CYCLE_HISTORY = 100


# ── Public write API ───────────────────────────────────────────────────────────

def record_request(method: str, path: str, status_code: int, duration: float) -> None:
    """Record a completed HTTP request."""
    with _lock:
        _request_counts[method][path] += 1
        if status_code >= 400:
            _request_errors[method][path] += 1
        samples = _latency_samples[method][path]
        samples.append(duration)
        if len(samples) > _MAX_LATENCY_SAMPLES:
            del samples[0]


def record_cycle(stats: dict) -> None:
    """Record a completed cycle run from the cycle stats dict."""
    with _lock:
        started = _parse_iso(stats.get("started_at", ""))
        finished = _parse_iso(stats.get("finished_at", ""))
        duration = finished - started if finished and started else 0.0
        entry = CycleStats(
            run_id=stats.get("run_id", ""),
            started_at=started,
            finished_at=finished,
            duration_seconds=duration,
            signals_harvested=stats.get("signals_harvested", 0),
            records_stored=stats.get("records_stored", 0),
            errors=len(stats.get("errors", [])),
            success=len(stats.get("errors", [])) == 0,
        )
        _cycle_history.append(entry)
        if len(_cycle_history) > _MAX_CYCLE_HISTORY:
            del _cycle_history[0]


# ── Public read API ────────────────────────────────────────────────────────────

def get_metrics_dict() -> dict:
    """Return all collected metrics as a Python dict."""
    with _lock:
        req_summary: dict = {}
        for method, paths in _request_counts.items():
            for path, count in paths.items():
                key = f"{method} {path}"
                errors = _request_errors[method][path]
                samples = _latency_samples[method][path]
                req_summary[key] = {
                    "requests_total": count,
                    "errors_total": errors,
                    "latency_p50_ms": _percentile(samples, 0.50) * 1000,
                    "latency_p99_ms": _percentile(samples, 0.99) * 1000,
                    "latency_mean_ms": (_mean(samples)) * 1000,
                }
        cycles = [
            {
                "run_id": c.run_id,
                "duration_seconds": round(c.duration_seconds, 3),
                "signals_harvested": c.signals_harvested,
                "records_stored": c.records_stored,
                "errors": c.errors,
                "success": c.success,
            }
            for c in _cycle_history
        ]
        last_cycle = cycles[-1] if cycles else None
        return {
            "requests": req_summary,
            "cycles": {
                "total": len(cycles),
                "last": last_cycle,
                "history": cycles,
            },
        }


def get_prometheus_text() -> str:
    """Return Prometheus exposition format text."""
    lines: list[str] = []
    with _lock:
        # API request metrics
        lines.append("# HELP spec1_http_requests_total Total HTTP requests")
        lines.append("# TYPE spec1_http_requests_total counter")
        for method, paths in _request_counts.items():
            for path, count in paths.items():
                labels = f'method="{method}",path="{path}"'
                lines.append(f"spec1_http_requests_total{{{labels}}} {count}")

        lines.append("# HELP spec1_http_errors_total Total HTTP errors (status >= 400)")
        lines.append("# TYPE spec1_http_errors_total counter")
        for method, paths in _request_errors.items():
            for path, count in paths.items():
                labels = f'method="{method}",path="{path}"'
                lines.append(f"spec1_http_errors_total{{{labels}}} {count}")

        lines.append("# HELP spec1_http_latency_p99_seconds Request latency p99 in seconds")
        lines.append("# TYPE spec1_http_latency_p99_seconds gauge")
        for method, paths in _latency_samples.items():
            for path, samples in paths.items():
                if samples:
                    labels = f'method="{method}",path="{path}"'
                    p99 = _percentile(samples, 0.99)
                    lines.append(f"spec1_http_latency_p99_seconds{{{labels}}} {p99:.6f}")

        # Cycle metrics
        lines.append("# HELP spec1_cycles_total Total intelligence cycles run")
        lines.append("# TYPE spec1_cycles_total counter")
        lines.append(f"spec1_cycles_total {len(_cycle_history)}")

        if _cycle_history:
            last = _cycle_history[-1]
            lines.append("# HELP spec1_cycle_duration_seconds Duration of last cycle")
            lines.append("# TYPE spec1_cycle_duration_seconds gauge")
            lines.append(f"spec1_cycle_duration_seconds {last.duration_seconds:.3f}")

            lines.append("# HELP spec1_cycle_signals_harvested Signals harvested in last cycle")
            lines.append("# TYPE spec1_cycle_signals_harvested gauge")
            lines.append(f"spec1_cycle_signals_harvested {last.signals_harvested}")

            lines.append("# HELP spec1_cycle_records_stored Records stored in last cycle")
            lines.append("# TYPE spec1_cycle_records_stored gauge")
            lines.append(f"spec1_cycle_records_stored {last.records_stored}")

            lines.append("# HELP spec1_cycle_success Whether last cycle succeeded (1=yes 0=no)")
            lines.append("# TYPE spec1_cycle_success gauge")
            lines.append(f"spec1_cycle_success {1 if last.success else 0}")

    return "\n".join(lines) + "\n"


def reset_metrics() -> None:
    """Reset all metrics (primarily for testing)."""
    with _lock:
        _request_counts.clear()
        _request_errors.clear()
        _latency_samples.clear()
        _cycle_history.clear()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    sorted_s = sorted(samples)
    idx = int(len(sorted_s) * p)
    idx = min(idx, len(sorted_s) - 1)
    return sorted_s[idx]


def _mean(samples: list[float]) -> float:
    return sum(samples) / len(samples) if samples else 0.0


def _parse_iso(s: str) -> float:
    """Parse an ISO-8601 timestamp to a Unix epoch float, or return 0.0."""
    if not s:
        return 0.0
    try:
        from datetime import datetime, timezone
        # Handle both 'Z' suffix and '+00:00' offset
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0

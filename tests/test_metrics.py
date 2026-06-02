"""Tests for spec1_api.metrics — in-process metrics collector."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_metrics():
    """Ensure metrics are cleared before and after each test."""
    from spec1_api import metrics as m
    m.reset_metrics()
    yield
    m.reset_metrics()


# ── record_request ─────────────────────────────────────────────────────────────

class TestRecordRequest:
    def test_increments_request_count(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/health", 200, 0.01)
        data = m.get_metrics_dict()
        assert data["requests"]["GET /health"]["requests_total"] == 1

    def test_counts_multiple_requests(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/health", 200, 0.01)
        m.record_request("GET", "/health", 200, 0.02)
        m.record_request("GET", "/health", 200, 0.03)
        data = m.get_metrics_dict()
        assert data["requests"]["GET /health"]["requests_total"] == 3

    def test_tracks_errors(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/intel", 200, 0.05)
        m.record_request("GET", "/intel", 404, 0.01)
        m.record_request("GET", "/intel", 500, 0.02)
        data = m.get_metrics_dict()
        assert data["requests"]["GET /intel"]["errors_total"] == 2

    def test_tracks_latency_p50(self):
        from spec1_api import metrics as m
        for d in [0.01, 0.02, 0.03, 0.04, 0.05]:
            m.record_request("POST", "/cycle/run", 200, d)
        data = m.get_metrics_dict()
        p50 = data["requests"]["POST /cycle/run"]["latency_p50_ms"]
        assert p50 > 0

    def test_different_methods_tracked_separately(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/intel", 200, 0.01)
        m.record_request("POST", "/intel", 201, 0.02)
        data = m.get_metrics_dict()
        assert "GET /intel" in data["requests"]
        assert "POST /intel" in data["requests"]

    def test_different_paths_tracked_separately(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/health", 200, 0.01)
        m.record_request("GET", "/signals", 200, 0.05)
        data = m.get_metrics_dict()
        assert "GET /health" in data["requests"]
        assert "GET /signals" in data["requests"]


# ── record_cycle ───────────────────────────────────────────────────────────────

class TestRecordCycle:
    def _make_stats(self, run_id="run-001", signals=10, records=5, errors=None):
        from datetime import datetime, timezone
        started = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc).isoformat()
        finished = datetime(2024, 1, 15, 6, 2, 30, tzinfo=timezone.utc).isoformat()
        return {
            "run_id": run_id,
            "started_at": started,
            "finished_at": finished,
            "signals_harvested": signals,
            "records_stored": records,
            "errors": errors or [],
        }

    def test_records_cycle(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats())
        data = m.get_metrics_dict()
        assert data["cycles"]["total"] == 1

    def test_last_cycle_has_run_id(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats(run_id="run-abc"))
        data = m.get_metrics_dict()
        assert data["cycles"]["last"]["run_id"] == "run-abc"

    def test_cycle_duration_computed(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats())
        data = m.get_metrics_dict()
        # started=06:00:00 finished=06:02:30 → 150s
        assert data["cycles"]["last"]["duration_seconds"] == pytest.approx(150.0, abs=1.0)

    def test_cycle_success_true_no_errors(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats(errors=[]))
        assert m.get_metrics_dict()["cycles"]["last"]["success"] is True

    def test_cycle_success_false_with_errors(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats(errors=["something failed"]))
        assert m.get_metrics_dict()["cycles"]["last"]["success"] is False

    def test_multiple_cycles_tracked(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats("run-001"))
        m.record_cycle(self._make_stats("run-002"))
        m.record_cycle(self._make_stats("run-003"))
        data = m.get_metrics_dict()
        assert data["cycles"]["total"] == 3
        assert data["cycles"]["last"]["run_id"] == "run-003"

    def test_signals_and_records_tracked(self):
        from spec1_api import metrics as m
        m.record_cycle(self._make_stats(signals=42, records=17))
        data = m.get_metrics_dict()
        assert data["cycles"]["last"]["signals_harvested"] == 42
        assert data["cycles"]["last"]["records_stored"] == 17


# ── get_prometheus_text ────────────────────────────────────────────────────────

class TestPrometheusText:
    def test_empty_metrics_returns_string(self):
        from spec1_api import metrics as m
        text = m.get_prometheus_text()
        assert isinstance(text, str)

    def test_request_counter_present_after_record(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/health", 200, 0.01)
        text = m.get_prometheus_text()
        assert "spec1_http_requests_total" in text
        assert 'method="GET"' in text
        assert 'path="/health"' in text

    def test_cycle_counter_after_record(self):
        from spec1_api import metrics as m
        from datetime import datetime, timezone
        stats = {
            "run_id": "run-x",
            "started_at": datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc).isoformat(),
            "finished_at": datetime(2024, 1, 15, 6, 1, tzinfo=timezone.utc).isoformat(),
            "signals_harvested": 5,
            "records_stored": 2,
            "errors": [],
        }
        m.record_cycle(stats)
        text = m.get_prometheus_text()
        assert "spec1_cycles_total" in text
        assert "spec1_cycle_duration_seconds" in text

    def test_error_metric_present(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/bad", 500, 0.1)
        text = m.get_prometheus_text()
        assert "spec1_http_errors_total" in text


# ── reset_metrics ──────────────────────────────────────────────────────────────

class TestResetMetrics:
    def test_reset_clears_requests(self):
        from spec1_api import metrics as m
        m.record_request("GET", "/health", 200, 0.01)
        m.reset_metrics()
        assert m.get_metrics_dict()["requests"] == {}

    def test_reset_clears_cycles(self):
        from spec1_api import metrics as m
        from datetime import datetime, timezone
        stats = {
            "run_id": "r",
            "started_at": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
            "finished_at": datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc).isoformat(),
            "signals_harvested": 1,
            "records_stored": 1,
            "errors": [],
        }
        m.record_cycle(stats)
        m.reset_metrics()
        assert m.get_metrics_dict()["cycles"]["total"] == 0

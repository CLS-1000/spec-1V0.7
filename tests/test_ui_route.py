"""Tests for the SPEC-1 UI root route (GET /)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """TestClient with scheduler mocked so no real APScheduler runs."""
    with patch("spec1_api.scheduler.start_scheduler"), \
         patch("spec1_api.scheduler.stop_scheduler"):
        from spec1_api.main import app
        with TestClient(app) as c:
            yield c


def test_root_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_root_contains_spec1_title(client):
    r = client.get("/")
    assert "SPEC-1 Intelligence Engine" in r.text


def test_root_contains_layout_div(client):
    r = client.get("/")
    assert 'class="layout"' in r.text

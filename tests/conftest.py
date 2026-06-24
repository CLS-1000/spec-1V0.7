"""Test configuration — mock network LLM calls to prevent hangs in CI."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True, scope="function")
def mock_network_llm_calls(request):
    """Mock network LLM calls only for cycle/briefing tests.

    Skips Tier 1 (Claude API) via SPEC1_DEV_MODE for tests that call
    run_cycle or briefing generator, since CI has no API credits.

    Fallback client tests are excluded so they can test Tier 1 behavior.
    """
    # Only apply mocking for specific test files
    test_module = request.fspath.basename
    if test_module in ("test_cycle.py", "test_api.py", "test_briefing.py"):
        os.environ["SPEC1_DEV_MODE"] = "true"

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="# Test Brief")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("spec1_core.llm.ollama_manager.chat", side_effect=Exception("Ollama offline")), \
             patch("anthropic.Anthropic", return_value=mock_client):
            yield
            os.environ.pop("SPEC1_DEV_MODE", None)
    else:
        yield

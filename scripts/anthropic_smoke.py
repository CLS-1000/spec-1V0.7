"""Anthropic API smoke test — verify the key and model are reachable.

Run from the repo root:
    python scripts/anthropic_smoke.py

Exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with: ok"}],
        )
        text = msg.content[0].text.strip() if msg.content else ""
        print(f"Anthropic API smoke test passed. Response: {text!r}")
    except Exception as exc:
        print(f"ERROR: Anthropic API call failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

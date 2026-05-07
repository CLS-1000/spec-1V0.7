"""Out-of-process PDF rendering.

Runs weasyprint in a subprocess so its native deps (Cairo, Pango, etc.)
are never loaded into the engine or API runtime.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_RENDER_SCRIPT = """\
import sys
from weasyprint import HTML
HTML(string=sys.stdin.read()).write_pdf(sys.argv[1])
"""


def render_html_to_pdf(html_content: str, output_path: Path) -> None:
    """Render *html_content* to a PDF file at *output_path*.

    Raises RuntimeError if weasyprint is not installed in the subprocess
    environment or if rendering fails.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, "-c", _RENDER_SCRIPT, str(output_path)],
        input=html_content.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"PDF rendering failed (exit {result.returncode}): {stderr}")


def brief_to_pdf(brief_md: str, output_path: Path) -> None:
    """Convert a Markdown brief to PDF via a minimal HTML wrapper."""
    try:
        import markdown
        html_body = markdown.markdown(brief_md, extensions=["tables", "fenced_code"])
    except ImportError:
        # Fallback: wrap in <pre> if markdown library not available
        escaped = brief_md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_body = f"<pre>{escaped}</pre>"

    html = (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:40px auto;line-height:1.6}</style>"
        f"</head><body>{html_body}</body></html>"
    )
    render_html_to_pdf(html, output_path)

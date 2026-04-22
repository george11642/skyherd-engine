"""Render a Markdown file to PDF using weasyprint.

Usage:
    uv run python scripts/render_pdf.py docs/ONE_PAGER.md docs/ONE_PAGER.pdf

Requires the [docs] optional dependency group:
    uv sync --extra docs
"""

from __future__ import annotations

import sys
from pathlib import Path

_CSS = """
@page {
    size: letter;
    margin: 1in;
}

body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
    max-width: 100%;
}

h1 {
    font-size: 20pt;
    font-weight: bold;
    margin-top: 0;
    margin-bottom: 4pt;
    border-bottom: 2px solid #1a1a1a;
    padding-bottom: 4pt;
}

h2 {
    font-size: 13pt;
    font-weight: bold;
    margin-top: 16pt;
    margin-bottom: 4pt;
}

h3 {
    font-size: 11pt;
    font-weight: bold;
    margin-top: 12pt;
    margin-bottom: 2pt;
}

p {
    margin: 6pt 0;
}

ul, ol {
    margin: 6pt 0;
    padding-left: 20pt;
}

li {
    margin-bottom: 2pt;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 8pt 0;
    font-size: 10pt;
}

th {
    background-color: #f0f0f0;
    border: 1px solid #cccccc;
    padding: 4pt 6pt;
    text-align: left;
    font-weight: bold;
}

td {
    border: 1px solid #cccccc;
    padding: 4pt 6pt;
}

pre, code {
    font-family: "Courier New", Courier, monospace;
    font-size: 9pt;
    background-color: #f8f8f8;
}

pre {
    padding: 8pt;
    border: 1px solid #dddddd;
    border-radius: 3px;
    overflow-x: auto;
    white-space: pre-wrap;
}

code {
    padding: 1pt 3pt;
    border-radius: 2px;
}

pre code {
    padding: 0;
    background: none;
}

blockquote {
    border-left: 3px solid #888888;
    margin-left: 0;
    padding-left: 12pt;
    color: #444444;
    font-style: italic;
}

hr {
    border: none;
    border-top: 1px solid #cccccc;
    margin: 12pt 0;
}

strong {
    font-weight: bold;
}

em {
    font-style: italic;
}

a {
    color: #1a1a1a;
    text-decoration: underline;
}
"""


def convert(md_path: str, pdf_path: str) -> None:
    """Convert a Markdown file to PDF.

    Parameters
    ----------
    md_path:
        Path to the source Markdown file.
    pdf_path:
        Destination path for the output PDF.
    """
    try:
        import markdown as md_lib  # type: ignore[import]
        from weasyprint import CSS, HTML  # type: ignore[import]
    except ImportError as exc:
        print(  # noqa: T201
            f"Missing dependency: {exc}\n"
            "Install docs extras: uv sync --extra docs",
            file=sys.stderr,
        )
        sys.exit(1)

    source = Path(md_path)
    if not source.exists():
        print(f"Input file not found: {md_path}", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    md_text = source.read_text(encoding="utf-8")

    # Convert Markdown to HTML with table + fenced-code extensions
    html_body = md_lib.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite"],
    )
    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"

    dest = Path(pdf_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=full_html, base_url=str(source.parent)).write_pdf(
        str(dest),
        stylesheets=[CSS(string=_CSS)],
    )

    size_kb = dest.stat().st_size // 1024
    print(f"PDF written: {dest} ({size_kb} KB)")  # noqa: T201


def main() -> None:
    if len(sys.argv) != 3:
        print(  # noqa: T201
            f"Usage: {sys.argv[0]} <input.md> <output.pdf>",
            file=sys.stderr,
        )
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()

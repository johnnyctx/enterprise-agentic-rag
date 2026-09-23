"""PDF -> Markdown conversion used by the ingestion pipeline.

The converter is intentionally isolated behind one function so the implementation can be
replaced later with an enterprise document-AI service without changing downstream RAG code.
"""
from __future__ import annotations

from pathlib import Path


def pdf_to_markdown(pdf_path: str | Path) -> str:
    """Convert a PDF into normalized Markdown using PyMuPDF4LLM."""
    try:
        import pymupdf4llm
    except ImportError as exc:  # pragma: no cover - exercised by environment setup
        raise RuntimeError(
            "PDF ingestion requires pymupdf4llm. Install with `pip install -e '.[pdf]'`."
        ) from exc

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path}")

    markdown = pymupdf4llm.to_markdown(str(path), page_chunks=False)
    return normalize_markdown(markdown)


def normalize_markdown(markdown: str) -> str:
    """Apply lightweight normalization while preserving headings and table structure."""
    lines = [line.rstrip() for line in markdown.replace("\r\n", "\n").split("\n")]
    output: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                output.append("")
            blank = True
            continue
        output.append(line)
        blank = False
    return "\n".join(output).strip() + "\n"

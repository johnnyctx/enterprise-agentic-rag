from __future__ import annotations

import re
from pathlib import Path


def normalize_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def pdf_to_markdown(pdf_path: str | Path) -> str:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError('Install PDF support with: pip install -e ".[pdf,dev]"') from exc
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.read_bytes()[:5] != b"%PDF-":
        raise ValueError(f"Not a PDF: {path}")
    return normalize_markdown(pymupdf4llm.to_markdown(str(path)))

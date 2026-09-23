"""End-to-end source ingestion pipeline.

PDF path:
    source PDF -> PDF-to-Markdown -> metadata -> Markdown artifact -> chunking/indexing

The Markdown artifact is the canonical text representation consumed by downstream RAG.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.pdf_to_markdown import pdf_to_markdown


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest_pdf(
    pdf_path: str | Path,
    markdown_dir: str | Path,
    *,
    source_url: str,
    document_id: str,
    title: str,
    access_level: str = "PUBLIC",
) -> Path:
    """Convert one PDF to Markdown and write a provenance-rich Markdown artifact."""
    pdf = Path(pdf_path)
    out_dir = Path(markdown_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    body = pdf_to_markdown(pdf)
    checksum = sha256(pdf)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    frontmatter = {
        "document_id": document_id,
        "title": title,
        "source_type": "pdf",
        "source_url": source_url,
        "source_file": pdf.name,
        "sha256": checksum,
        "retrieved_at": retrieved_at,
        "access_level": access_level,
        "conversion": "pymupdf4llm",
        "content_type": "text/markdown",
    }

    target = out_dir / f"{document_id}.md"
    target.write_text(
        "---\n" + json.dumps(frontmatter, indent=2) + "\n---\n\n" + body,
        encoding="utf-8",
    )
    return target

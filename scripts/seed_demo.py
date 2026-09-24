"""Offline seed path for tests/local development.

The production-shaped path is scripts/upload_corpus.py -> S3 -> SQS -> worker.
This script is intentionally deterministic and does not require AWS services.
"""
from pathlib import Path

from app.config import settings
from app.ingestion.chunker import chunk_document, load_markdown
from app.rag.store import HybridIndex


def main() -> None:
    source = Path("data/vanguard_public/converted_markdown")
    index = HybridIndex(settings.index_path)
    paths = sorted(source.glob("*.md"))
    total = 0
    for path in paths:
        total += len((chunks := chunk_document(load_markdown(path))))
        index.add(chunks)
    print(f"Indexed {total} chunks from {len(paths)} Markdown documents into {settings.index_path}.")


if __name__ == "__main__":
    main()

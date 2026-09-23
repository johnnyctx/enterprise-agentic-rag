from pathlib import Path
from app.api.main import store
from app.ingestion.chunker import load_markdown, chunk_document

paths = list(Path("data/vanguard_public").glob("*.md"))
paths += list(Path("data/vanguard_public/converted_markdown").glob("*.md"))

for p in paths:
    source_url = "https://www.vanguard.com/"
    store.add(chunk_document(load_markdown(p, source_url)))

print(f"Loaded {len(store.chunks)} chunks from {len(paths)} Markdown documents.")

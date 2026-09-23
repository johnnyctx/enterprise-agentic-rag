import re
from pathlib import Path
from app.rag.models import Document, Chunk

def load_markdown(path: str, source_url: str) -> Document:
    p = Path(path)
    return Document(p.stem, p.stem.replace("_"," ").title(),
                    p.read_text(encoding="utf-8"), source_url)

def chunk_document(doc: Document, max_chars: int = 900) -> list[Chunk]:
    chunks, offset = [], 0
    section = "Document"
    for i, block in enumerate(re.split(r"\n(?=#)", doc.text)):
        block = block.strip()
        if not block:
            continue
        heading = re.search(r"^#{1,6}\s+(.+)$", block, re.M)
        if heading:
            section = heading.group(1).strip()
        start = max(doc.text.find(block, offset), offset)
        offset = start + len(block)
        pieces = [block[j:j+max_chars] for j in range(0, len(block), max_chars)]
        local = start
        for j, piece in enumerate(pieces):
            chunks.append(Chunk(f"{doc.doc_id}#{i}_{j}", doc.doc_id, doc.title,
                                piece, doc.source_url, section, doc.access_level,
                                local, local+len(piece)))
            local += len(piece)
    return chunks

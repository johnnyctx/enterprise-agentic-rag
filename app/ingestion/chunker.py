from __future__ import annotations

import json
import re
from pathlib import Path

from app.rag.models import Chunk, Document

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TOKEN_RE = re.compile(r"\S+")


def _parse_scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {'"', "'"} and value[-1:] == value[0]:
        return value[1:-1]
    if value.lower() in {"null", "none"}:
        return ""
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1).strip()
    # Current pipeline emits JSON inside YAML delimiters; the downloader emits YAML scalars.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}, text[match.end():]
    except json.JSONDecodeError:
        pass
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = _parse_scalar(value)
    return metadata, text[match.end():]


def load_markdown(path: str | Path, source_url: str | None = None) -> Document:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(raw)
    doc_id = metadata.get("document_id") or metadata.get("id") or p.stem
    title = metadata.get("title") or p.stem.replace("_", " ").title()
    return Document(
        doc_id=doc_id,
        title=title,
        text=body.strip() + "\n",
        source_url=metadata.get("source_url") or source_url or "",
        access_level=metadata.get("access_level", "PUBLIC").upper(),
        version=metadata.get("version", metadata.get("document_version", "1")),
        source_type=metadata.get("source_type", metadata.get("document_type", "pdf")),
        source_file=metadata.get("source_file", metadata.get("source_pdf", p.name)),
        source_sha256=metadata.get("sha256", ""),
        retrieved_at=metadata.get("retrieved_at", ""),
        converted_at=metadata.get("converted_at", ""),
        content_type=metadata.get("content_type", "text/markdown"),
    )


def _logical_blocks(text: str) -> list[tuple[str, str, int, int]]:
    lines = text.splitlines(keepends=True)
    blocks: list[tuple[str, str, int, int]] = []
    current: list[str] = []
    current_start = 0
    section = "Document"
    offset = 0

    def flush(end_offset: int) -> None:
        nonlocal current, current_start
        content = "".join(current).strip()
        if content:
            left = text.find(content, current_start, end_offset)
            left = current_start if left < 0 else left
            blocks.append((section, content, left, left + len(content)))
        current = []

    for line in lines:
        stripped = line.strip()
        heading = _HEADING_RE.match(stripped)
        if heading:
            flush(offset)
            section = heading.group(2).strip()
            current_start = offset
            current = [line]
        elif not stripped:
            flush(offset)
            current_start = offset + len(line)
        else:
            if not current:
                current_start = offset
            current.append(line)
        offset += len(line)
    flush(offset)
    return blocks


def _split_oversized(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_chars:
            pieces.append(remaining)
            break
        cut = remaining.rfind(". ", 0, max_chars)
        if cut < max_chars // 2:
            cut = remaining.rfind(" ", 0, max_chars)
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return pieces


def chunk_document(doc: Document, max_chars: int = 1200, overlap: int = 120) -> list[Chunk]:
    if max_chars <= overlap:
        raise ValueError("max_chars must be greater than overlap")
    chunks: list[Chunk] = []
    index = 0
    for section, block, start, end in _logical_blocks(doc.text):
        pieces = _split_oversized(block, max_chars)
        cursor = start
        for piece in pieces:
            if not piece:
                continue
            actual_start = doc.text.find(piece, cursor, end + 1)
            actual_start = cursor if actual_start < 0 else actual_start
            actual_end = actual_start + len(piece)
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{index:05d}",
                    doc_id=doc.doc_id,
                    title=doc.title,
                    text=piece,
                    source_url=doc.source_url,
                    section=section,
                    access_level=doc.access_level,
                    char_start=actual_start,
                    char_end=actual_end,
                    document_version=doc.version,
                    source_type=doc.source_type,
                    source_file=doc.source_file,
                    source_sha256=doc.source_sha256,
                    retrieved_at=doc.retrieved_at,
                    converted_at=doc.converted_at,
                    content_type=doc.content_type,
                    chunk_index=index,
                )
            )
            index += 1
            cursor = max(actual_start + len(piece) - overlap, actual_start + 1)
    return chunks

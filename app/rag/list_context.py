from __future__ import annotations

import re

from app.rag.models import Chunk

_GENERIC = {
    "document", "introduction", "conclusion", "references", "reference",
    "notes on risk", "source", "vanguard research", "appendix",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _is_structure_label(text: str) -> bool:
    clean = _clean(text)
    clean = re.sub(r"^#{1,6}\s+", "", clean)
    clean = re.sub(r"^\*\*(.*?)\*\*$", r"\1", clean)
    clean = clean.rstrip(".")
    if not clean or clean.lower() in _GENERIC or re.match(r"^appendix(?:\s+\d+)?$", clean.lower()):
        return False
    terms = re.findall(r"[a-z0-9]+", clean.lower())
    return 1 <= len(terms) <= 4 and len(clean) <= 48


def _heading_text(text: str) -> str:
    clean = _clean(text)
    clean = re.sub(r"^#{1,6}\s+", "", clean)
    clean = re.sub(r"^\*\*(.*?)\*\*$", r"\1", clean)
    return clean.rstrip(".")


def select_list_context(chunks: list[Chunk], ranked: list[Chunk], limit: int = 20) -> list[Chunk]:
    """Build a structure-aware context for a document-scoped LIST query.

    Retrieval scores alone tend to favor body chunks that mention generic query
    terms. This selector preserves high-ranked evidence while adding the first
    substantive chunk following document-level principle labels.
    """
    if not chunks:
        return ranked[:limit]

    ordered = sorted(chunks, key=lambda c: c.chunk_index)
    selected: list[Chunk] = []
    seen: set[str] = set()

    def add(chunk: Chunk) -> None:
        if chunk.chunk_id not in seen and len(selected) < limit:
            selected.append(chunk)
            seen.add(chunk.chunk_id)

    # Preserve the strongest retrieval evidence first.
    for chunk in ranked:
        add(chunk)
        if len(selected) >= min(8, limit):
            break

    # Find short structural labels such as Goals, Balance, Cost, and Discipline.
    # For each label, prefer the next substantive chunk rather than returning the
    # label itself. This recovers principle headings even when PDF extraction made
    # the heading a standalone chunk.
    for pos, chunk in enumerate(ordered):
        label_source = chunk.text if _is_structure_label(chunk.text) else chunk.section
        if not _is_structure_label(label_source):
            continue
        label = _heading_text(label_source).lower()
        if label in _GENERIC or label.startswith("appendix"):
            continue
            continue
        for candidate in ordered[pos + 1:]:
            if candidate.doc_id != chunk.doc_id:
                break
            candidate_text = _clean(candidate.text)
            if _is_structure_label(candidate_text) and _heading_text(candidate_text).lower() != label:
                break
            # Prefer a detailed principle heading/body; skip source/reference noise.
            if candidate.section.lower().strip() in _GENERIC:
                continue
            if len(re.findall(r"[a-z0-9]+", candidate_text.lower())) >= 4:
                add(candidate)
                break

    return selected[:limit]

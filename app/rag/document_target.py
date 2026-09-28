from __future__ import annotations

import re
from collections import defaultdict

from app.rag.models import Chunk

_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "described", "do", "does",
    "for", "from", "how", "in", "is", "it", "of", "on", "or", "the", "this", "to",
    "what", "which", "with", "document", "key", "main", "list", "identify",
}


def _terms(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in _STOP and len(x) > 1}


def _stem(term: str) -> str:
    if len(term) > 5 and term.endswith("ing"):
        return term[:-3]
    if len(term) > 5 and term.endswith("ed"):
        return term[:-2]
    if len(term) > 4 and term.endswith("s"):
        return term[:-1]
    return term


def _normalized(text: str) -> set[str]:
    return {_stem(x) for x in _terms(text)}


def select_target_document(query: str, chunks: list[Chunk]) -> tuple[str | None, str]:
    """Identify a document explicitly implied by a LIST question.

    LIST questions are vulnerable to cross-document contamination because a large
    public corpus can contain several documents about the same subject. Prefer a
    document whose title has strong lexical alignment with the question, then
    constrain downstream ranking/generation to that document.
    """
    if not chunks:
        return None, "no candidate chunks"

    query_terms = _normalized(query)
    by_doc: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        by_doc[chunk.doc_id].append(chunk)

    candidates: list[tuple[float, int, str, str]] = []
    for doc_id, doc_chunks in by_doc.items():
        title = max((c.title for c in doc_chunks), key=len, default="")
        title_terms = _normalized(title)
        overlap = len(query_terms & title_terms)
        ratio = overlap / max(1, len(query_terms))
        # A title with two or more meaningful query terms is a strong explicit
        # target signal. One shared generic term such as "Vanguard" is not.
        if overlap >= 2:
            candidates.append((ratio, overlap, doc_id, title))

    if not candidates:
        return None, "no document title matched at least two query terms"

    candidates.sort(reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and best[:2] == candidates[1][:2]:
        return None, "document target ambiguous"
    return best[2], f"selected '{best[3]}' from {best[1]} title-term matches"

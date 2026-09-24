from __future__ import annotations

import re

from app.rag.models import Chunk


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _overlap(query_terms: set[str], text: str) -> float:
    terms = _terms(text)
    return len(query_terms & terms) / max(1, len(query_terms))


def rerank(query: str, chunks: list[Chunk]) -> list[Chunk]:
    """Rerank retrieved chunks without discarding the retrieval signal.

    The original hybrid score remains the primary signal. Query overlap with
    title and section metadata provides additional topical relevance, while
    body overlap remains a secondary signal.
    """
    q = _terms(query)
    scored: list[tuple[float, Chunk]] = []

    for chunk in chunks:
        body_overlap = _overlap(q, chunk.text)
        title_overlap = _overlap(q, chunk.title)
        section_overlap = _overlap(q, chunk.section)

        score = (
            0.60 * chunk.score
            + 0.15 * chunk.lexical_score
            + 0.10 * chunk.vector_score
            + 0.10 * title_overlap
            + 0.05 * section_overlap
        )

        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        Chunk(
            **{
                **chunk.__dict__,
                "score": score,
                "retrieval_rank": rank,
            }
        )
        for rank, (score, chunk) in enumerate(scored, 1)
    ]
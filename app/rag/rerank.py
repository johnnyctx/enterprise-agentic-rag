from __future__ import annotations

import re

from app.rag.models import Chunk


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def _terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9]+", text.lower())
        if term not in _STOPWORDS
    }


def _normalize_terms(terms: set[str]) -> set[str]:
    normalized = set()

    for term in terms:
        if len(term) > 4 and term.endswith("ing"):
            term = term[:-3]
        elif len(term) > 5 and term.endswith("ed"):
            term = term[:-2]
        elif len(term) > 4 and term.endswith("s"):
            term = term[:-1]

        normalized.add(term)

    return normalized


def _overlap(query_terms: set[str], text: str) -> float:
    text_terms = _normalize_terms(_terms(text))
    normalized_query = _normalize_terms(query_terms)

    return len(normalized_query & text_terms) / max(1, len(normalized_query))


def rerank(query: str, chunks: list[Chunk]) -> list[Chunk]:
    """Rerank retrieved chunks using retrieval and topical metadata signals.

    The hybrid retrieval score remains part of the ranking, while document
    title and section relevance provide stronger topical signals for short
    or heading-heavy chunks.
    """
    query_terms = _terms(query)

    scored: list[tuple[float, Chunk]] = []

    for chunk in chunks:
        title_overlap = _overlap(query_terms, chunk.title)
        section_overlap = _overlap(query_terms, chunk.section)
        body_overlap = _overlap(query_terms, chunk.text)

        score = (
            0.25 * chunk.score
            + 0.10 * chunk.lexical_score
            + 0.05 * chunk.vector_score
            + 0.45 * title_overlap
            + 0.10 * section_overlap
            + 0.05 * body_overlap
        )

        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

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

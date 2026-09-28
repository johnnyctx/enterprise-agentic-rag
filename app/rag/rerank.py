from __future__ import annotations

import re

from app.rag.models import Chunk


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "what", "when", "where", "which", "who", "why", "with",
}

_LIST_PATTERNS = (
    r"\bwhat are\b",
    r"\bkey .*principles\b",
    r"\bmain .*principles\b",
    r"\bwhat .*principles\b",
    r"\blist\b",
    r"\bidentify\b",
    r"\bwhich .*principles\b",
)

_GENERIC_SECTIONS = {
    "document", "introduction", "conclusion", "references", "reference", "notes on risk",
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


def is_list_query(query: str) -> bool:
    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in _LIST_PATTERNS)


def _is_heading_only(text: str) -> bool:
    clean = re.sub(r"\s+", " ", text.strip())
    return bool(clean) and bool(re.fullmatch(r"#{1,6}\s+.+", clean))


def _section_quality(section: str) -> float:
    normalized = re.sub(r"\s+", " ", section.strip().lower())
    if normalized in _GENERIC_SECTIONS:
        return 0.0
    # A real heading is useful evidence for a list answer even when the heading
    # does not repeat the user's exact words (for example, "Create clear,
    # appropriate investment goals").
    return 1.0 if normalized else 0.0


def rerank(query: str, chunks: list[Chunk], route: str | None = None) -> list[Chunk]:
    """Rerank retrieved chunks while preserving evidence-oriented metadata.

    For list/"what are the principles" questions, document titles are deliberately
    down-weighted because every chunk in the same document has the same title.
    Section and body relevance become the stronger signals, and generic
    introduction/conclusion/reference sections are de-emphasized.
    """
    query_terms = _terms(query)
    list_query = route == "LIST" or is_list_query(query)
    scored: list[tuple[float, Chunk]] = []

    for chunk in chunks:
        title_overlap = _overlap(query_terms, chunk.title)
        section_overlap = _overlap(query_terms, chunk.section)
        body_overlap = _overlap(query_terms, chunk.text)
        section_quality = _section_quality(chunk.section)
        heading_only = _is_heading_only(chunk.text)

        if list_query:
            score = (
                0.20 * chunk.score
                + 0.05 * chunk.lexical_score
                + 0.05 * chunk.vector_score
                + 0.05 * title_overlap
                + 0.25 * section_overlap
                + 0.30 * body_overlap
                + 0.10 * section_quality
            )
            if section_quality == 0.0:
                score *= 0.70
            if heading_only:
                score *= 0.20
        else:
            score = (
                0.25 * chunk.score
                + 0.10 * chunk.lexical_score
                + 0.05 * chunk.vector_score
                + 0.35 * title_overlap
                + 0.15 * section_overlap
                + 0.10 * body_overlap
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

from __future__ import annotations

import re

from app.rag.models import Citation, Chunk

_CITATION_RE = re.compile(r"\[S(\d+)\]")


def build_citations(chunks: list[Chunk]) -> list[Citation]:
    return [
        Citation(
            span_id=f"S{i}",
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            title=chunk.title,
            text=chunk.text,
            source_url=chunk.source_url,
            section=chunk.section,
            retrieval_rank=chunk.retrieval_rank,
        )
        for i, chunk in enumerate(chunks, 1)
    ]


def referenced_span_ids(answer: str) -> set[str]:
    return {f"S{n}" for n in _CITATION_RE.findall(answer)}


def validate_citations(answer: str, citations: list[Citation]) -> list[str]:
    allowed = {c.span_id for c in citations}
    referenced = referenced_span_ids(answer)
    warnings = [f"Answer references unknown citation {span}." for span in sorted(referenced - allowed)]
    if not referenced and answer.strip() and answer != "INSUFFICIENT_EVIDENCE":
        warnings.append("Answer contains no evidence citation markers.")
    return warnings

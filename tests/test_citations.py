from app.rag.citations import build_citations, validate_citations
from app.rag.models import Chunk


def test_unknown_citation_is_rejected():
    chunk = Chunk("d#1", "d", "Doc", "Evidence text.", "https://example.test", "S", "PUBLIC", 0, 10, retrieval_rank=1)
    citations = build_citations([chunk])
    warnings = validate_citations("Evidence text. [S9]", citations)
    assert warnings

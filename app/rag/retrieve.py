from __future__ import annotations

from app.rag.models import Chunk, RetrievalTrace
from app.rag.store import HybridIndex


class Retriever:
    def __init__(self, store: HybridIndex):
        self.store = store
        self.last_trace: RetrievalTrace | None = None

    def retrieve(self, query: str, access_level: str = "PUBLIC", top_k: int = 8) -> list[Chunk]:
        chunks = self.store.hybrid_search(query, access_level, top_k)
        self.last_trace = RetrievalTrace(
            query=query,
            lexical_candidates=len(self.store.lexical_search(query, {"PUBLIC", "INTERNAL", "RESTRICTED"}, top_k * 4)),
            vector_candidates=len(self.store.vector_search(query, {"PUBLIC", "INTERNAL", "RESTRICTED"}, top_k * 4)),
            fused_candidates=len(chunks),
            authorized_candidates=len(chunks),
            top_k=top_k,
        )
        return chunks

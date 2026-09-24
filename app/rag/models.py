from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AccessLevel = Literal["PUBLIC", "INTERNAL", "RESTRICTED"]


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str
    source_url: str
    access_level: AccessLevel = "PUBLIC"
    version: str = "1"
    source_type: str = "pdf"
    source_file: str = ""
    source_sha256: str = ""
    retrieved_at: str = ""
    converted_at: str = ""
    content_type: str = "text/markdown"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    source_url: str
    section: str
    access_level: AccessLevel
    char_start: int
    char_end: int
    document_version: str = "1"
    source_type: str = "pdf"
    source_file: str = ""
    source_sha256: str = ""
    retrieved_at: str = ""
    converted_at: str = ""
    content_type: str = "text/markdown"
    chunk_index: int = 0
    retrieval_rank: int = 0
    score: float = 0.0
    lexical_score: float = 0.0
    vector_score: float = 0.0


@dataclass(frozen=True)
class Citation:
    span_id: str
    chunk_id: str
    doc_id: str
    title: str
    text: str
    source_url: str
    section: str
    retrieval_rank: int


@dataclass(frozen=True)
class ClaimValidation:
    claim: str
    status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "UNSUPPORTED"]
    evidence: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass(frozen=True)
class RetrievalTrace:
    query: str
    lexical_candidates: int
    vector_candidates: int
    fused_candidates: int
    authorized_candidates: int
    top_k: int


@dataclass(frozen=True)
class AgentDecision:
    route: str
    query: str
    search_queries: list[str]
    attempt: int
    max_attempts: int
    reason: str

from dataclasses import dataclass, field
from typing import Literal

AccessLevel = Literal["PUBLIC", "INTERNAL", "RESTRICTED"]

@dataclass
class Document:
    doc_id: str
    title: str
    text: str
    source_url: str
    access_level: AccessLevel = "PUBLIC"
    version: str = "1"

@dataclass
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
    retrieval_rank: int = 0
    score: float = 0.0

@dataclass
class Citation:
    span_id: str
    chunk_id: str
    doc_id: str
    title: str
    text: str
    source_url: str
    section: str
    retrieval_rank: int

@dataclass
class ClaimValidation:
    claim: str
    status: Literal["SUPPORTED","PARTIALLY_SUPPORTED","CONTRADICTED","UNSUPPORTED"]
    evidence: list[str] = field(default_factory=list)
    reason: str = ""

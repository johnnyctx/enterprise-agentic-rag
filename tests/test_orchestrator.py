from pathlib import Path

from app.agents.orchestrator import AgentOrchestrator
from app.llm.demo import DeterministicLLM
from app.rag.retrieve import Retriever
from app.rag.store import HybridIndex
from app.rag.models import Chunk


def test_unsupported_internal_request_is_refused(tmp_path: Path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    index.add([Chunk("d#1", "d", "Doc", "Public financial wellness content.", "https://example.test", "S", "PUBLIC", 0, 30)])
    result = AgentOrchestrator(Retriever(index), DeterministicLLM()).run("What is the internal AWS architecture?")
    assert result["refused"] is True
    assert result["confidence"] == 0.0


def test_supported_request_gets_citations(tmp_path: Path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    index.add([Chunk("d#1", "d", "Doc", "Investing success depends on goals, diversification, and costs.", "https://example.test", "Principles", "PUBLIC", 0, 70)])
    result = AgentOrchestrator(Retriever(index), DeterministicLLM()).run("What are the principles for investing success?")
    assert result["refused"] is False
    assert result["citations"]

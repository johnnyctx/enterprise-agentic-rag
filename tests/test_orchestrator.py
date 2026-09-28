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


def test_list_query_does_not_mix_documents(tmp_path: Path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    index.add([
        Chunk("fw#1", "fw", "Vanguard's guide to financial wellness", "Taxable accounts can be used for many long-term goals. By investing in taxable accounts, you gain tax diversification.", "https://example.test/fw", "What goals should taxable accounts be used for?", "PUBLIC", 0, 150),
        Chunk("p#1", "p", "Vanguard's Principles for Investing Success", "Create clear, appropriate investment goals. Investors should establish clear and appropriate investment goals.", "https://example.test/p", "Create clear, appropriate investment goals", "PUBLIC", 0, 100),
        Chunk("p#2", "p", "Vanguard's Principles for Investing Success", "Minimize costs. Keeping costs low can improve the amount of return retained by an investor.", "https://example.test/p", "Minimize costs", "PUBLIC", 0, 100),
        Chunk("p#3", "p", "Vanguard's Principles for Investing Success", "Maintain perspective and long-term discipline. Discipline in investing is the ability to adhere, over time, to an investment plan.", "https://example.test/p", "Maintain perspective and long-term discipline", "PUBLIC", 0, 140),
    ])
    result = AgentOrchestrator(Retriever(index), DeterministicLLM()).run(
        "What are the key principles for investing success described in Vanguard's document?"
    )
    assert result["refused"] is False
    assert result["debug"]["target_doc_id"] == "p"
    assert all(c["doc_id"] == "p" for c in result["citations"])
    assert "taxable" not in result["answer"].lower()


def test_list_query_extracts_short_principle_statements(tmp_path: Path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    title = "Vanguard's Principles for Investing Success"
    index.add([
        Chunk("p#1", "p", title, "**Goals**", "https://example.test/p", "Document", "PUBLIC", 0, 10, chunk_index=1),
        Chunk("p#2", "p", title, "Create clear, appropriate investment goals. Investors should establish clear and appropriate investment goals.", "https://example.test/p", "Document", "PUBLIC", 10, 110, chunk_index=2),
        Chunk("p#3", "p", title, "**Balance**", "https://example.test/p", "Document", "PUBLIC", 110, 120, chunk_index=3),
        Chunk("p#4", "p", title, "Keep a balanced and diversified mix of investments. Diversification can reduce portfolio volatility.", "https://example.test/p", "Document", "PUBLIC", 120, 220, chunk_index=4),
        Chunk("p#5", "p", title, "**Cost**", "https://example.test/p", "Document", "PUBLIC", 220, 230, chunk_index=5),
        Chunk("p#6", "p", title, "Minimize costs. Keeping costs low can improve the amount of return retained by an investor.", "https://example.test/p", "Document", "PUBLIC", 230, 330, chunk_index=6),
        Chunk("p#7", "p", title, "**Discipline**", "https://example.test/p", "Document", "PUBLIC", 330, 340, chunk_index=7),
        Chunk("p#8", "p", title, "Maintain perspective and long-term discipline. Discipline means adhering to an investment plan.", "https://example.test/p", "Document", "PUBLIC", 340, 440, chunk_index=8),
    ])
    result = AgentOrchestrator(Retriever(index), DeterministicLLM()).run(
        "What are the key principles for investing success described in Vanguard's document?"
    )
    assert result["refused"] is False
    assert "Create clear, appropriate investment goals." in result["answer"]
    assert "Keep a balanced and diversified mix of investments." in result["answer"]
    assert "Minimize costs." in result["answer"]
    assert "Maintain perspective and long-term discipline." in result["answer"]


def test_list_query_excludes_appendix_research_description(tmp_path: Path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    title = "Vanguard's Principles for Investing Success"
    index.add([
        Chunk("p#1", "p", title, "Create clear, appropriate investment goals.", "https://example.test/p", "Goals", "PUBLIC", 0, 50, chunk_index=1),
        Chunk("p#2", "p", title, "Keep a balanced and diversified mix of investments.", "https://example.test/p", "Balance", "PUBLIC", 50, 110, chunk_index=2),
        Chunk("p#3", "p", title, "Minimize costs.", "https://example.test/p", "Cost", "PUBLIC", 110, 130, chunk_index=3),
        Chunk("p#4", "p", title, "Maintain perspective and long-term discipline.", "https://example.test/p", "Discipline", "PUBLIC", 130, 190, chunk_index=4),
        Chunk("p#5", "p", title, "Appendix 1: Vanguard's Principles for Investing Success is a body of research that intends to capture important and evergreen considerations for investors across regions and with a robust view of the markets.", "https://example.test/p", "Appendix 1", "PUBLIC", 190, 350, chunk_index=5),
    ])
    result = AgentOrchestrator(Retriever(index), DeterministicLLM()).run(
        "What are the key principles for investing success described in Vanguard's document?"
    )
    assert result["refused"] is False
    assert "Appendix 1:" not in result["answer"]
    assert "body of research" not in result["answer"]
    assert "Create clear, appropriate investment goals." in result["answer"]
    assert "Keep a balanced and diversified mix of investments." in result["answer"]
    assert "Minimize costs." in result["answer"]
    assert "Maintain perspective and long-term discipline." in result["answer"]


def test_list_query_excludes_document_title(tmp_path: Path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    title = "Vanguard's Principles for Investing Success"
    index.add([
        Chunk("p#0", "p", title, "#### **Vanguard's Principles for Investing Success**", "https://example.test/p", title, "PUBLIC", 0, 50, chunk_index=0),
        Chunk("p#1", "p", title, "Create clear, appropriate investment goals.", "https://example.test/p", "Goals", "PUBLIC", 50, 100, chunk_index=1),
        Chunk("p#2", "p", title, "Keep a balanced and diversified mix of investments.", "https://example.test/p", "Balance", "PUBLIC", 100, 160, chunk_index=2),
        Chunk("p#3", "p", title, "Minimize costs.", "https://example.test/p", "Cost", "PUBLIC", 160, 190, chunk_index=3),
        Chunk("p#4", "p", title, "Maintain perspective and long-term discipline.", "https://example.test/p", "Discipline", "PUBLIC", 190, 250, chunk_index=4),
    ])
    result = AgentOrchestrator(Retriever(index), DeterministicLLM()).run(
        "What are the key principles for investing success described in Vanguard's document?"
    )
    assert result["refused"] is False
    assert "Vanguard's Principles for Investing Success." not in result["answer"]
    assert result["answer"].count("[S") == 4

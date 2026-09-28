from app.rag.models import Chunk
from app.rag.rerank import rerank


def make_chunk(i, section, text, score):
    return Chunk(
        f"d#{i}", "d", "Vanguard's Principles for Investing Success", text,
        "https://example.test", section, "PUBLIC", 0, len(text), score=score,
        lexical_score=score, vector_score=score,
    )


def test_list_rerank_does_not_promote_generic_sections_over_principles():
    chunks = [
        make_chunk(0, "Introduction", "These principles provide a framework for investors seeking success.", 0.90),
        make_chunk(1, "Conclusion", "These principles can provide a framework for investors.", 0.88),
        make_chunk(2, "Create clear, appropriate investment goals", "Investors should establish clear and appropriate investment goals.", 0.65),
        make_chunk(3, "Develop a suitable asset allocation", "A suitable asset allocation should reflect the investor's goals and risk tolerance.", 0.62),
        make_chunk(4, "Save more and invest consistently", "Saving and investing consistently can contribute to long-term investment success.", 0.60),
    ]
    ranked = rerank("What are the key principles for investing success?", chunks, route="LIST")
    top_sections = {chunk.section for chunk in ranked[:3]}
    assert top_sections == {
        "Create clear, appropriate investment goals",
        "Develop a suitable asset allocation",
        "Save more and invest consistently",
    }


def test_list_rerank_penalizes_heading_only_chunks():
    chunks = [
        make_chunk(0, "Create clear, appropriate investment goals", "### Create clear, appropriate investment goals", 0.90),
        make_chunk(1, "Create clear, appropriate investment goals", "Investors should establish clear and appropriate investment goals.", 0.65),
        make_chunk(2, "Develop a suitable asset allocation", "A suitable asset allocation should reflect the investor's goals and risk tolerance.", 0.62),
    ]
    ranked = rerank("What are the key principles for investing success?", chunks, route="LIST")
    assert ranked[0].chunk_id == "d#1"


def test_list_target_document_selection_avoids_cross_document_contamination():
    from app.rag.document_target import select_target_document

    chunks = [
        Chunk("fw#1", "fw", "Vanguard's guide to financial wellness", "Taxable accounts can be used for long-term goals.", "https://example.test/fw", "Taxable accounts", "PUBLIC", 0, 50),
        Chunk("p#1", "p", "Vanguard's Principles for Investing Success", "Minimize costs.", "https://example.test/p", "Principles", "PUBLIC", 0, 20),
        Chunk("p#2", "p", "Vanguard's Principles for Investing Success", "Maintain perspective and long-term discipline.", "https://example.test/p", "Discipline", "PUBLIC", 0, 50),
    ]
    doc_id, reason = select_target_document(
        "What are the key principles for investing success described in Vanguard's document?",
        chunks,
    )
    assert doc_id == "p"
    assert "Principles for Investing Success" in reason

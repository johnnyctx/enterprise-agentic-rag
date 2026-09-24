from app.rag.models import Chunk
from app.rag.store import HybridIndex


def chunk(i, text, level="PUBLIC"):
    return Chunk(f"d#{i}", "d", "Doc", text, "https://example.test", "S", level, 0, len(text), chunk_index=i)


def test_hybrid_retrieval_combines_signals(tmp_path):
    index = HybridIndex(tmp_path / "index.sqlite3")
    index.add([
        chunk(0, "Financial wellness includes emergency savings and spending plans."),
        chunk(1, "Investing success depends on goals, diversification, and costs."),
        chunk(2, "Unrelated tax administration information."),
    ])
    result = index.hybrid_search("investing success diversification", "PUBLIC", 2)
    assert result
    assert result[0].chunk_id == "d#1"

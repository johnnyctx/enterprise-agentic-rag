from pathlib import Path

from app.ingestion.chunker import chunk_document, load_markdown


def test_frontmatter_and_sections_are_preserved(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text('---\n{"document_id":"d1","title":"Example","source_url":"https://example.test","sha256":"abc","access_level":"PUBLIC"}\n---\n\n# Section One\n\nAlpha beta gamma.\n\n## Section Two\n\nDelta epsilon.\n', encoding="utf-8")
    doc = load_markdown(p)
    chunks = chunk_document(doc, max_chars=160)
    assert doc.doc_id == "d1"
    assert doc.source_sha256 == "abc"
    assert {c.section for c in chunks} == {"Section One", "Section Two"}
    assert all(c.source_url == "https://example.test" for c in chunks)

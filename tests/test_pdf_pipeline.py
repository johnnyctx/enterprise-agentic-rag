from pathlib import Path

from app.ingestion.pdf_to_markdown import normalize_markdown


def test_normalize_markdown_preserves_headings_and_collapses_blanks():
    text = "# Heading\n\n\nBody  \n\n\nNext"
    assert normalize_markdown(text) == "# Heading\n\nBody\n\nNext\n"


def test_pdf_manifest_contains_five_public_sources():
    manifest = Path("data/vanguard_public/pdf_manifest.json").read_text(encoding="utf-8")
    assert manifest.count('"url":') >= 5
    assert "vanguards_guide_to_financial_wellness.pdf" in manifest

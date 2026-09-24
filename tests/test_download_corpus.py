from pathlib import Path

from scripts import download_corpus


def test_download_corpus_only_targets_pdf_source_directory():
    assert download_corpus.PDF_OUTPUT_DIR == (
        Path(download_corpus.PROJECT_ROOT) / "data" / "vanguard_public" / "source_pdfs"
    )
    assert not hasattr(download_corpus, "MARKDOWN_OUTPUT_DIR")
    assert not hasattr(download_corpus, "convert_pdf_to_markdown")
    assert not hasattr(download_corpus, "build_markdown_with_provenance")

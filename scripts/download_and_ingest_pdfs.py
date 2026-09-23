#!/usr/bin/env python3
"""
Download selected public Vanguard PDF documents and convert them to Markdown.

Pipeline:

    Vanguard PDF URL
        ↓
    HTTPS download with certificate verification
        ↓
    PDF validation
        ↓
    SHA-256 checksum
        ↓
    PDF → Markdown
        ↓
    Normalized Markdown artifact
        ↓
    Provenance metadata

The downloaded PDFs are intentionally not committed to Git.
They are reproducible source artifacts downloaded from the URLs in
data/vanguard_public/pdf_manifest.json.

Usage:

    python scripts/download_and_ingest_pdfs.py

Requirements:

    pip install -e ".[pdf,dev]"
"""

from __future__ import annotations

import hashlib
import json
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = PROJECT_ROOT / "data" / "vanguard_public"

MANIFEST_PATH = DATA_ROOT / "pdf_manifest.json"

PDF_OUTPUT_DIR = DATA_ROOT / "source_pdfs"

MARKDOWN_OUTPUT_DIR = DATA_ROOT / "converted_markdown"


# ---------------------------------------------------------------------------
# HTTPS configuration
# ---------------------------------------------------------------------------

# Use the CA bundle provided by certifi rather than relying exclusively on
# the operating system's Python certificate configuration.
#
# This is particularly useful on macOS installations where Python may not
# automatically discover the system CA certificates.

SSL_CONTEXT = ssl.create_default_context(
    cafile=certifi.where()
)


USER_AGENT = (
    "enterprise-agentic-rag/1.0 "
    "(public-document-ingestion)"
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """
    Calculate the SHA-256 checksum of a file.

    Reading in chunks avoids loading large PDFs entirely into memory.
    """
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def validate_pdf(path: Path) -> None:
    """
    Perform a lightweight PDF validation.

    This catches cases where a web server returns an HTML error page
    instead of the expected PDF.
    """
    if not path.exists():
        raise RuntimeError(f"PDF does not exist: {path}")

    if path.stat().st_size == 0:
        raise RuntimeError(f"Downloaded PDF is empty: {path}")

    with path.open("rb") as file:
        header = file.read(5)

    if header != b"%PDF-":
        raise RuntimeError(
            f"Downloaded file does not appear to be a PDF: {path}"
        )


def download_pdf(url: str, destination: Path) -> None:
    """
    Download a PDF over HTTPS.

    TLS certificate verification remains enabled.
    The certifi CA bundle is explicitly supplied to avoid common
    macOS Python certificate-chain problems.
    """

    print(f"Downloading {url}")

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*",
        },
    )

    try:
        with urlopen(
            request,
            timeout=60,
            context=SSL_CONTEXT,
        ) as response:

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            data = response.read()

    except HTTPError as exc:
        raise RuntimeError(
            f"HTTP error downloading {url}: "
            f"{exc.code} {exc.reason}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Network error downloading {url}: {exc.reason}"
        ) from exc

    if not data:
        raise RuntimeError(
            f"Server returned an empty response for {url}"
        )

    # Write the file before validation so that validation can inspect
    # the exact artifact that will be used by the pipeline.
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(data)

    try:
        validate_pdf(destination)
    except RuntimeError:
        # If a server returned HTML or another unexpected response,
        # remove the invalid artifact rather than leaving it in the
        # source_pdfs directory.
        destination.unlink(missing_ok=True)

        raise RuntimeError(
            f"Downloaded content was not a valid PDF.\n"
            f"URL: {url}\n"
            f"Content-Type: {content_type or 'unknown'}"
        )

    print(
        f"  ✓ Downloaded "
        f"{destination.stat().st_size / 1024:.1f} KB"
    )


def convert_pdf_to_markdown(
    pdf_path: Path,
    markdown_path: Path,
) -> None:
    """
    Convert a PDF to Markdown using PyMuPDF4LLM.

    PyMuPDF4LLM is deliberately isolated behind this function so that
    the document conversion implementation can later be replaced with
    another parser without changing the rest of the ingestion pipeline.
    """

    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF4LLM is not installed.\n\n"
            "Install the PDF dependencies with:\n\n"
            '    pip install -e ".[pdf,dev]"'
        ) from exc

    print(
        f"Converting {pdf_path.name} → Markdown ..."
    )

    markdown = pymupdf4llm.to_markdown(
        str(pdf_path)
    )

    if not markdown.strip():
        raise RuntimeError(
            f"PDF conversion produced empty Markdown: "
            f"{pdf_path}"
        )

    markdown_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    markdown_path.write_text(
        markdown,
        encoding="utf-8",
    )

    print(
        f"  ✓ Markdown generated: "
        f"{markdown_path}"
    )


def build_markdown_with_provenance(
    markdown_path: Path,
    item: dict,
    pdf_path: Path,
) -> None:
    """
    Add reproducibility/provenance information to the Markdown artifact.
    """

    existing_markdown = markdown_path.read_text(
        encoding="utf-8"
    )

    checksum = sha256_file(pdf_path)

    generated_at = utc_timestamp()

    provenance = f"""---
document_id: {item["id"]}
title: {item["title"]}
source: Vanguard
source_url: {item["url"]}
document_type: pdf
source_pdf: {pdf_path.name}
sha256: {checksum}
converted_at: {generated_at}
converter: PyMuPDF4LLM
---

"""

    markdown_path.write_text(
        provenance + existing_markdown,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------

def main() -> int:
    """Run the complete Vanguard PDF ingestion pipeline."""

    print()
    print("=" * 72)
    print("Enterprise Agentic RAG — Vanguard PDF Ingestion")
    print("=" * 72)
    print()

    if not MANIFEST_PATH.exists():
        print(
            f"ERROR: PDF manifest not found:\n"
            f"  {MANIFEST_PATH}",
            file=sys.stderr,
        )

        return 1

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    documents = manifest.get("documents", [])

    if not documents:
        print(
            "ERROR: No documents found in PDF manifest.",
            file=sys.stderr,
        )

        return 1

    PDF_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    MARKDOWN_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Found {len(documents)} PDF documents in manifest."
    )

    print()

    failures: list[dict] = []

    for index, item in enumerate(
        documents,
        start=1,
    ):

        title = item["title"]
        document_id = item["id"]
        url = item["url"]

        print("-" * 72)
        print(
            f"[{index}/{len(documents)}] {title}"
        )
        print("-" * 72)

        pdf_filename = item.get(
            "filename",
            f"{document_id}.pdf",
        )

        markdown_filename = item.get(
            "markdown_filename",
            f"{document_id}.md",
        )

        pdf_path = PDF_OUTPUT_DIR / pdf_filename

        markdown_path = (
            MARKDOWN_OUTPUT_DIR /
            markdown_filename
        )

        try:
            # --------------------------------------------------------------
            # 1. Download
            # --------------------------------------------------------------

            if pdf_path.exists():
                print(
                    f"PDF already exists: "
                    f"{pdf_path}"
                )

                validate_pdf(pdf_path)

            else:
                download_pdf(
                    url,
                    pdf_path,
                )

            # --------------------------------------------------------------
            # 2. Checksum
            # --------------------------------------------------------------

            checksum = sha256_file(
                pdf_path
            )

            print(
                f"  ✓ SHA-256: {checksum}"
            )

            # --------------------------------------------------------------
            # 3. PDF → Markdown
            # --------------------------------------------------------------

            convert_pdf_to_markdown(
                pdf_path,
                markdown_path,
            )

            # --------------------------------------------------------------
            # 4. Add provenance
            # --------------------------------------------------------------

            build_markdown_with_provenance(
                markdown_path,
                item,
                pdf_path,
            )

            print(
                "  ✓ Provenance metadata added"
            )

            print()

        except Exception as exc:
            print(
                f"  ✗ FAILED: {exc}",
                file=sys.stderr,
            )

            failures.append(
                {
                    "id": document_id,
                    "title": title,
                    "url": url,
                    "error": str(exc),
                }
            )

            print()

    # -----------------------------------------------------------------------
    # Final result
    # -----------------------------------------------------------------------

    print("=" * 72)

    if failures:
        print(
            f"INGESTION FAILED: "
            f"{len(failures)} document(s) failed."
        )

        print()

        for failure in failures:
            print(
                f"- {failure['title']}: "
                f"{failure['error']}"
            )

        print()

        print(
            "Successful artifacts remain available in:"
        )

        print(
            f"  {PDF_OUTPUT_DIR}"
        )

        print(
            f"  {MARKDOWN_OUTPUT_DIR}"
        )

        return 1

    print(
        f"INGESTION COMPLETE: "
        f"{len(documents)} document(s) processed successfully."
    )

    print()

    print("PDF files:")
    print(
        f"  {PDF_OUTPUT_DIR}"
    )

    print()

    print("Markdown files:")
    print(
        f"  {MARKDOWN_OUTPUT_DIR}"
    )

    print()

    print(
        "Pipeline:"
    )

    print(
        "  PDF → validation → SHA-256 → "
        "PDF → Markdown → provenance"
    )

    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
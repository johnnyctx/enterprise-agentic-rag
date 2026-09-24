#!/usr/bin/env python3
"""
Download selected public Vanguard PDF documents for the demonstration corpus.

Pipeline:

    Vanguard PDF URL
        ↓
    HTTPS download with certificate verification
        ↓
    PDF validation
        ↓
    SHA-256 checksum
        ↓
    local source_pdfs/

The downloaded PDFs are intentionally not committed to Git.
They are reproducible source artifacts downloaded from the URLs in
data/vanguard_public/pdf_manifest.json.

Usage:

    python scripts/download_corpus.py

Requirements:

    pip install -e ".[dev]"
"""

from __future__ import annotations

import hashlib
import json
import ssl
import sys
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
    "(public-corpus-downloader)"
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


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


def main() -> int:
    """Download the public demonstration PDFs listed in the manifest."""
    print()
    print("=" * 72)
    print("Enterprise Agentic RAG — Public Demo Corpus Downloader")
    print("=" * 72)
    print()

    if not MANIFEST_PATH.exists():
        print(f"ERROR: PDF manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    documents = manifest.get("documents", [])
    if not documents:
        print("ERROR: No documents found in PDF manifest.", file=sys.stderr)
        return 1

    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []

    print(f"Found {len(documents)} PDF documents in manifest.")
    print()

    for index, item in enumerate(documents, start=1):
        title = item["title"]
        document_id = item["id"]
        url = item["url"]
        pdf_filename = item.get("filename", f"{document_id}.pdf")
        pdf_path = PDF_OUTPUT_DIR / pdf_filename

        print("-" * 72)
        print(f"[{index}/{len(documents)}] {title}")
        print("-" * 72)

        try:
            if pdf_path.exists():
                print(f"PDF already exists: {pdf_path}")
                validate_pdf(pdf_path)
            else:
                download_pdf(url, pdf_path)

            print(f"  ✓ SHA-256: {sha256_file(pdf_path)}")
            print()
        except Exception as exc:
            print(f"  ✗ FAILED: {exc}", file=sys.stderr)
            failures.append({"id": document_id, "title": title, "url": url, "error": str(exc)})
            print()

    print("=" * 72)
    if failures:
        print(f"DOWNLOAD FAILED: {len(failures)} document(s) failed.")
        for failure in failures:
            print(f"- {failure['title']}: {failure['error']}")
        return 1

    print(f"DOWNLOAD COMPLETE: {len(documents)} document(s) available.")
    print(f"PDF files: {PDF_OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

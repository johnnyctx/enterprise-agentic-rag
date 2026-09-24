"""Upload the manifest's PDFs to S3 and rely on S3 notification -> SQS."""
from __future__ import annotations

import json
import os
from pathlib import Path

import boto3

from app.config import settings


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/vanguard_public/pdf_manifest.json"
PDF_DIR = ROOT / "data/vanguard_public/source_pdfs"


def main() -> None:
    s3 = boto3.client(
        "s3", region_name=settings.aws_region, endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest["documents"]:
        path = PDF_DIR / item["filename"]
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run scripts/download_corpus.py first.")
        key = f"documents/{path.name}"
        s3.upload_file(
            str(path), settings.s3_bucket, key,
            ExtraArgs={
                "ContentType": "application/pdf",
                "Metadata": {
                    "source-url": item["url"],
                    "title": item["title"],
                    "access-level": "PUBLIC",
                },
            },
        )
        print(f"uploaded s3://{settings.s3_bucket}/{key}")


if __name__ == "__main__":
    main()

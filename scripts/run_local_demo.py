"""Download public demo PDFs, upload them, and wait for the worker to index them."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import boto3

from app.config import settings

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run(["python", "scripts/download_corpus.py"], cwd=ROOT, check=True)
    subprocess.run(["python", "scripts/upload_corpus.py"], cwd=ROOT, check=True)
    dynamodb = boto3.client(
        "dynamodb", region_name=settings.aws_region, endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )
    expected = len(json.loads((ROOT / "data/vanguard_public/pdf_manifest.json").read_text())["documents"])
    for _ in range(60):
        count = int(dynamodb.scan(TableName=settings.metadata_table, Select="COUNT")["Count"])
        if count >= expected:
            print(f"Indexed {count} documents.")
            return
        time.sleep(2)
    raise SystemExit("Timed out waiting for ingestion worker")


if __name__ == "__main__":
    main()

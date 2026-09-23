#!/usr/bin/env python3
"""Refresh the public demonstration corpus from its authoritative source URLs.

The checked-in markdown files are curated source-backed snapshots. This script can be
used when network access is available to fetch the current HTML pages and save them under
data/vanguard_public/raw/. It intentionally keeps the curated snapshots separate from raw
HTML so evaluation data remains reproducible.
"""
from pathlib import Path
import json
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "vanguard_public"
RAW = DATA / "raw"
MANIFEST = DATA / "manifest.json"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for doc in manifest["documents"]:
        target = RAW / f"{doc['id']}.html"
        req = Request(doc["url"], headers={"User-Agent": "enterprise-agentic-rag-corpus-refresh/0.1"})
        with urlopen(req, timeout=30) as response:
            target.write_bytes(response.read())
        print(f"Fetched {doc['url']} -> {target}")
    print("Raw source pages refreshed. Curated snapshots were not overwritten.")

if __name__ == "__main__":
    main()

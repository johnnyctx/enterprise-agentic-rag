from __future__ import annotations

from app.rag.models import Chunk

ORDER = {"PUBLIC": 0, "INTERNAL": 1, "RESTRICTED": 2}


def normalize_access_level(value: str) -> str:
    value = (value or "PUBLIC").upper()
    if value not in ORDER:
        raise ValueError(f"Unsupported access level: {value}")
    return value


def filter_authorized(chunks: list[Chunk], access_level: str) -> list[Chunk]:
    level = ORDER[normalize_access_level(access_level)]
    # Security boundary: filter before context construction/generation.
    return [chunk for chunk in chunks if ORDER.get(chunk.access_level, 99) <= level]

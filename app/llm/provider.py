from __future__ import annotations

from typing import Protocol

from app.rag.models import Chunk


class LLMProvider(Protocol):
    def generate(self, question: str, chunks: list[Chunk]) -> str: ...

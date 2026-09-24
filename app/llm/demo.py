from __future__ import annotations

import re

from app.rag.models import Chunk

_STOP = {"what", "is", "are", "the", "a", "an", "to", "of", "for", "in", "on", "how", "does", "do", "and", "or", "with", "i", "we", "you"}


def _terms(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in _STOP and len(x) > 1}


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]


class DeterministicLLM:
    """Offline deterministic generator used for repeatable integration tests."""

    def generate(self, question: str, chunks: list[Chunk]) -> str:
        if not chunks:
            return "INSUFFICIENT_EVIDENCE"
        q = _terms(question)
        candidates: list[tuple[float, int, str]] = []
        for idx, chunk in enumerate(chunks, 1):
            for sentence in _sentences(chunk.text):
                st = _terms(sentence)
                overlap = len(q & st) / max(1, len(q))
                if overlap:
                    candidates.append((overlap + chunk.score, idx, sentence))
        candidates.sort(reverse=True)
        selected: list[str] = []
        used = set()
        for _, idx, sentence in candidates:
            key = (idx, sentence)
            if key in used:
                continue
            used.add(key)
            selected.append(f"{sentence} [S{idx}]")
            if len(selected) == 3:
                break
        if not selected:
            selected = [f"{_sentences(chunks[0].text)[0]} [S1]"]
        return " ".join(selected)

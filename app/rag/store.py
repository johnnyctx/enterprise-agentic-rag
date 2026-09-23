import re
from collections import Counter
from .models import Chunk

def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

class InMemoryHybridStore:
    def __init__(self):
        self.chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk]) -> None:
        self.chunks.extend(chunks)

    def search(self, query: str, access_level: str = "PUBLIC", top_k: int = 6) -> list[Chunk]:
        q = Counter(tokens(query))
        allowed = {"PUBLIC"}
        if access_level == "INTERNAL":
            allowed |= {"INTERNAL"}
        elif access_level == "RESTRICTED":
            allowed |= {"INTERNAL", "RESTRICTED"}
        scored = []
        for c in self.chunks:
            if c.access_level not in allowed:
                continue
            ct = Counter(tokens(c.text))
            lexical = sum(min(q[t], ct[t]) for t in q)
            phrase = 3.0 if query.lower() in c.text.lower() else 0.0
            score = lexical + phrase
            if score:
                scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [Chunk(**{**c.__dict__, "retrieval_rank": i, "score": float(s)})
                for i, (s, c) in enumerate(scored[:top_k], 1)]

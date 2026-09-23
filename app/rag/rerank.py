from .models import Chunk
from .store import tokens

def rerank(query: str, chunks: list[Chunk]) -> list[Chunk]:
    q = set(tokens(query))
    scored = [(c.score + .25*len(q & set(tokens(c.text))), c) for c in chunks]
    scored.sort(key=lambda x:x[0], reverse=True)
    return [Chunk(**{**c.__dict__, "score":s}) for s,c in scored]

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

from app.rag.models import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.I)
_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from", "how", "in", "is", "it", "of", "on", "or", "the", "to", "what", "with"}


def tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _terms(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in _STOP and len(t) > 1]


def _vector(text: str, dimensions: int = 256) -> list[float]:
    values = [0.0] * dimensions
    terms = _terms(text)
    if not terms:
        return values
    counts = Counter(terms)
    # Feature hashing gives a deterministic, dependency-free local embedding.
    for term, count in counts.items():
        digest = hashlib.blake2b(term.encode(), digest_size=8).digest()
        idx = int.from_bytes(digest, "big") % dimensions
        sign = 1.0 if digest[0] & 1 else -1.0
        values[idx] += sign * (1.0 + math.log1p(count))
    norm = math.sqrt(sum(x * x for x in values)) or 1.0
    return [x / norm for x in values]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class HybridIndex:
    """Persistent local hybrid index.

    SQLite FTS5 provides lexical retrieval; deterministic hashed vectors provide a
    fully offline vector path. Production can replace this class with OpenSearch
    while keeping the Retriever contract unchanged.
    """

    def __init__(self, path: str | Path = "data/runtime/index.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                source_url TEXT NOT NULL,
                section TEXT NOT NULL,
                access_level TEXT NOT NULL,
                char_start INTEGER NOT NULL,
                char_end INTEGER NOT NULL,
                document_version TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                converted_at TEXT NOT NULL,
                content_type TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                vector_json TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                text,
                title,
                section
            );
            """
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def clear(self) -> None:
        self._db.execute("DELETE FROM chunks")
        self._db.execute("DELETE FROM chunks_fts")
        self._db.commit()

    def add(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._db.execute(
                """
                INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                  title=excluded.title, text=excluded.text, source_url=excluded.source_url,
                  section=excluded.section, access_level=excluded.access_level,
                  document_version=excluded.document_version, source_sha256=excluded.source_sha256,
                  retrieved_at=excluded.retrieved_at, converted_at=excluded.converted_at,
                  vector_json=excluded.vector_json
                """,
                (
                    chunk.chunk_id, chunk.doc_id, chunk.title, chunk.text, chunk.source_url,
                    chunk.section, chunk.access_level, chunk.char_start, chunk.char_end,
                    chunk.document_version, chunk.source_type, chunk.source_file,
                    chunk.source_sha256, chunk.retrieved_at, chunk.converted_at,
                    chunk.content_type, chunk.chunk_index, json.dumps(_vector(chunk.text)),
                ),
            )
            self._db.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (chunk.chunk_id,))
            self._db.execute(
                "INSERT INTO chunks_fts(chunk_id,text,title,section) VALUES (?,?,?,?)",
                (chunk.chunk_id, chunk.text, chunk.title, chunk.section),
            )
        self._db.commit()

    def _row_to_chunk(self, row: sqlite3.Row, **scores) -> Chunk:
        return Chunk(
            chunk_id=row["chunk_id"], doc_id=row["doc_id"], title=row["title"], text=row["text"],
            source_url=row["source_url"], section=row["section"], access_level=row["access_level"],
            char_start=row["char_start"], char_end=row["char_end"],
            document_version=row["document_version"], source_type=row["source_type"],
            source_file=row["source_file"], source_sha256=row["source_sha256"],
            retrieved_at=row["retrieved_at"], converted_at=row["converted_at"],
            content_type=row["content_type"], chunk_index=row["chunk_index"], **scores,
        )

    def lexical_search(self, query: str, allowed_levels: set[str], limit: int = 30) -> list[Chunk]:
        terms = _terms(query)
        if not terms:
            return []
        match = " OR ".join('"' + t.replace('"', '') + '"' for t in terms)
        rows = self._db.execute(
            """
            SELECT c.*, bm25(chunks_fts, 1.0, 0.5, 0.5) AS bm
            FROM chunks_fts f JOIN chunks c ON c.chunk_id=f.chunk_id
            WHERE chunks_fts MATCH ? AND c.access_level IN ({levels})
            ORDER BY bm ASC LIMIT ?
            """.format(levels=",".join("?" for _ in allowed_levels)),
            (match, *sorted(allowed_levels), limit),
        ).fetchall()
        if not rows:
            return []
        raw = [-float(r["bm"]) for r in rows]
        lo, hi = min(raw), max(raw)
        def norm(x: float) -> float:
            return 1.0 if hi == lo else (x - lo) / (hi - lo)
        return [self._row_to_chunk(r, lexical_score=norm(x), score=norm(x)) for r, x in zip(rows, raw)]

    def vector_search(self, query: str, allowed_levels: set[str], limit: int = 30) -> list[Chunk]:
        qv = _vector(query)
        rows = self._db.execute(
            "SELECT * FROM chunks WHERE access_level IN ({})".format(",".join("?" for _ in allowed_levels)),
            tuple(sorted(allowed_levels)),
        ).fetchall()
        scored = []
        for row in rows:
            score = max(0.0, _cosine(qv, json.loads(row["vector_json"])))
            scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._row_to_chunk(row, vector_score=score, score=score) for score, row in scored[:limit] if score > 0]

    def hybrid_search(self, query: str, access_level: str, top_k: int = 8) -> list[Chunk]:
        allowed = {"PUBLIC"}
        if access_level in {"INTERNAL", "RESTRICTED"}:
            allowed.add("INTERNAL")
        if access_level == "RESTRICTED":
            allowed.add("RESTRICTED")
        lexical = self.lexical_search(query, allowed, max(30, top_k * 4))
        vector = self.vector_search(query, allowed, max(30, top_k * 4))
        by_id: dict[str, dict] = {}
        for rank, chunk in enumerate(lexical, 1):
            by_id.setdefault(chunk.chunk_id, {"chunk": chunk, "lex_rank": rank, "vec_rank": None})["lex_rank"] = rank
        for rank, chunk in enumerate(vector, 1):
            entry = by_id.setdefault(chunk.chunk_id, {"chunk": chunk, "lex_rank": None, "vec_rank": rank})
            entry["vec_rank"] = rank
            if entry["chunk"].lexical_score == 0:
                entry["chunk"] = chunk
        fused = []
        k = 60.0
        for entry in by_id.values():
            rrf = (1.0 / (k + entry["lex_rank"]) if entry["lex_rank"] else 0.0) + (1.0 / (k + entry["vec_rank"]) if entry["vec_rank"] else 0.0)
            chunk = entry["chunk"]
            fused.append((rrf, chunk))
        fused.sort(key=lambda x: x[0], reverse=True)
        return [
            Chunk(**{**c.__dict__, "score": score, "retrieval_rank": i})
            for i, (score, c) in enumerate(fused[:top_k], 1)
        ]

    def get_chunks(self, ids: list[str]) -> list[Chunk]:
        if not ids:
            return []
        rows = self._db.execute(
            "SELECT * FROM chunks WHERE chunk_id IN ({})".format(",".join("?" for _ in ids)), ids
        ).fetchall()
        mapping = {row["chunk_id"]: self._row_to_chunk(row) for row in rows}
        return [mapping[i] for i in ids if i in mapping]


# Backward-compatible name for small examples.
InMemoryHybridStore = HybridIndex

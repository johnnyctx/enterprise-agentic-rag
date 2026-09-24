from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.agents.orchestrator import AgentOrchestrator
from app.ingestion.chunker import chunk_document, load_markdown
from app.llm.provider import LLMProvider
from app.llm.bedrock import build_llm
from app.rag.retrieve import Retriever
from app.rag.store import HybridIndex

app = FastAPI(title="Enterprise Agentic RAG", version="1.0.0")
store = HybridIndex(settings.index_path)
retriever = Retriever(store)
generator: LLMProvider = build_llm(settings.llm_provider, settings.model_name, settings.aws_region)
orchestrator = AgentOrchestrator(retriever, generator)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    access_level: str = "PUBLIC"


@app.get("/health")
def health():
    return {"status": "ok", "indexed_chunks": store.count(), "llm_provider": settings.llm_provider}


@app.get("/ready")
def ready():
    if store.count() == 0:
        raise HTTPException(status_code=503, detail="Knowledge index is empty")
    return {"status": "ready", "indexed_chunks": store.count()}


@app.post("/query")
def query(request: QueryRequest):
    return orchestrator.run(request.query, request.access_level)

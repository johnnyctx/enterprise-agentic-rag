from fastapi import FastAPI
from pydantic import BaseModel, Field
from app.agents.orchestrator import AgentOrchestrator
from app.rag.store import InMemoryHybridStore
from app.rag.retrieve import Retriever

app=FastAPI(title="Enterprise Agentic RAG",version="0.1.0")
store=InMemoryHybridStore()

class QueryRequest(BaseModel):
    query:str=Field(min_length=1)
    access_level:str="PUBLIC"

@app.get("/health")
def health(): return {"status":"ok"}

@app.post("/query")
def query(request:QueryRequest):
    return AgentOrchestrator(Retriever(store)).run(request.query,request.access_level)

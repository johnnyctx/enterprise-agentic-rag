import json
from pathlib import Path
from app.api.main import store
from app.agents.orchestrator import AgentOrchestrator
from app.rag.retrieve import Retriever
from app.ingestion.chunker import load_markdown, chunk_document

for p in Path("data/vanguard_public").glob("*.md"):
    store.add(chunk_document(load_markdown(p,f"https://example.invalid/{p.name}")))
o=AgentOrchestrator(Retriever(store))
for case in json.loads(Path("evaluation/datasets/questions.json").read_text()):
    r=o.run(case["question"])
    print(json.dumps({"id":case["id"],"expected":case["expected"],"refused":r["refused"],"confidence":r["confidence"],"answer":r["answer"]}))

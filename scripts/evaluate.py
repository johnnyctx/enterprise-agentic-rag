from __future__ import annotations

import json
from pathlib import Path

from app.agents.orchestrator import AgentOrchestrator
from app.config import settings
from app.llm.bedrock import build_llm
from app.rag.retrieve import Retriever
from app.rag.store import HybridIndex


def main() -> int:
    cases = json.loads(Path("evaluation/datasets/questions.json").read_text(encoding="utf-8"))
    index = HybridIndex(settings.index_path)
    orchestrator = AgentOrchestrator(Retriever(index), build_llm(settings.llm_provider, settings.model_name, settings.aws_region))
    results = []
    for case in cases:
        response = orchestrator.run(case["question"])
        actual = "refused" if response["refused"] else "supported"
        passed = actual == case["expected"]
        results.append({"id": case["id"], "expected": case["expected"], "actual": actual, "passed": passed, "confidence": response["confidence"]})
        print(json.dumps({"id": case["id"], "passed": passed, "answer": response["answer"], "confidence": response["confidence"]}))
    passed = sum(r["passed"] for r in results)
    print(json.dumps({"passed": passed, "total": len(results), "accuracy": passed / max(1, len(results))}, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

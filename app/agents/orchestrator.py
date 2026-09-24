from __future__ import annotations

from app.agents.router import classify, expand_query
from app.config import settings
from app.observability.audit import audit_event, new_correlation_id
from app.rag.answer_relevance import evaluate_answer_relevance
from app.rag.answer_support import validate_claims
from app.rag.citations import build_citations, validate_citations
from app.rag.confidence import confidence
from app.rag.rerank import rerank
from app.rag.retrieve import Retriever
from app.security.authz import filter_authorized, normalize_access_level


class AgentOrchestrator:
    """Bounded evidence-driven agent loop.

    The loop is intentionally deterministic locally: route -> retrieve -> rerank ->
    generate -> validate -> retry with a broadened query when evidence is weak.
    A production deployment can swap the planner/generator without changing gates.
    """

    def __init__(self, retriever: Retriever, generator, max_attempts: int | None = None):
        self.retriever = retriever
        self.generator = generator
        self.max_attempts = max_attempts or settings.max_agent_attempts

    def run(self, query: str, access_level: str = "PUBLIC") -> dict:
        access_level = normalize_access_level(access_level)
        correlation_id = new_correlation_id()
        route = classify(query)
        audit_event("query_classified", route=route, query_length=len(query), access_level=access_level)
        if route == "UNSUPPORTED":
            return self.refusal(query, "The requested internal/private information is outside this public demonstration corpus.", route)

        attempts = []
        best = None
        for attempt in range(self.max_attempts):
            search_query = expand_query(query, route, attempt)
            audit_event("retrieval_started", attempt=attempt + 1, route=route)
            raw = self.retriever.retrieve(search_query, access_level, top_k=10)
            ranked = filter_authorized(rerank(search_query, raw), access_level)
            context = ranked[:4]
            citations = build_citations(context)
            answer = self.generator.generate(query, context)
            warnings = validate_citations(answer, citations)
            relevance, relevant, relevance_reason = evaluate_answer_relevance(query, answer, citations)
            claims = validate_claims(answer, citations)
            support = sum(c.status == "SUPPORTED" for c in claims) / max(1, len(claims))
            contradicted = any(c.status == "CONTRADICTED" for c in claims)
            unsupported = any(c.status == "UNSUPPORTED" for c in claims)
            citation_integrity = 1.0 if not warnings else 0.0
            retrieval_quality = min(1.0, (context[0].score * 80.0) if context else 0.0)
            candidate_refused = (not relevant) or contradicted or unsupported or not context or not citations
            score, label = confidence(retrieval_quality, citation_integrity, relevance, support, candidate_refused)
            attempt_result = {
                "attempt": attempt + 1,
                "search_query": search_query,
                "answer": answer,
                "relevance": relevance,
                "support": support,
                "confidence": score,
                "refused": candidate_refused,
                "warnings": warnings,
                "claim_statuses": [c.status for c in claims],
                "chunk_ids": [c.chunk_id for c in context],
            }
            attempts.append(attempt_result)
            best = (answer, citations, claims, warnings, relevance, relevance_reason, score, label, context)
            audit_event("attempt_evaluated", attempt=attempt + 1, refused=candidate_refused, confidence=score)
            if not candidate_refused and score >= 0.50:
                break

        assert best is not None
        answer, citations, claims, warnings, relevance, relevance_reason, score, label, context = best
        refused = not (score >= 0.50 and relevance >= 0.45 and not warnings and not any(c.status in {"UNSUPPORTED", "CONTRADICTED"} for c in claims))
        if refused:
            audit_event("query_refused", attempts=len(attempts), reason="evidence_validation_gate")
            return {
                "query": query,
                "answer": "INSUFFICIENT_EVIDENCE",
                "citations": [],
                "confidence": 0.0,
                "confidence_label": "refused",
                "refused": True,
                "warnings": warnings or ["Evidence validation gate failed."],
                "claims": [c.__dict__ for c in claims],
                "debug": {
                    "route": route,
                    "correlation_id": correlation_id,
                    "attempts": attempts,
                    "answer_relevance": relevance,
                    "answer_relevance_reason": relevance_reason,
                    "ranked_chunk_ids": [c.chunk_id for c in context],
                },
            }
        audit_event("query_completed", attempts=len(attempts), confidence=score)
        return {
            "query": query,
            "answer": answer,
            "citations": [c.__dict__ for c in citations],
            "confidence": score,
            "confidence_label": label,
            "refused": False,
            "warnings": warnings,
            "claims": [c.__dict__ for c in claims],
            "debug": {
                "route": route,
                "correlation_id": correlation_id,
                "attempts": attempts,
                "answer_relevance": relevance,
                "answer_relevance_reason": relevance_reason,
                "ranked_chunk_ids": [c.chunk_id for c in context],
            },
        }

    @staticmethod
    def refusal(query: str, reason: str, route: str) -> dict:
        return {
            "query": query,
            "answer": "INSUFFICIENT_EVIDENCE",
            "citations": [],
            "confidence": 0.0,
            "confidence_label": "refused",
            "refused": True,
            "warnings": [reason],
            "claims": [],
            "debug": {"route": route, "attempts": []},
        }

from app.agents.router import classify
from app.observability.audit import audit_event
from app.rag.answer_relevance import evaluate_answer_relevance
from app.rag.answer_support import validate_claims
from app.rag.citations import build_citations, validate_citations
from app.rag.confidence import confidence
from app.rag.generator import DemoLLM
from app.rag.rerank import rerank
from app.security.authz import filter_authorized

class AgentOrchestrator:
    def __init__(self,retriever,generator=None):
        self.retriever=retriever; self.generator=generator or DemoLLM()

    def run(self,query,access_level="PUBLIC"):
        route=classify(query); audit_event("query_classified",route=route)
        if route=="UNSUPPORTED":
            return self.refusal(query,"Requested information is outside the demonstration corpus.")
        chunks=filter_authorized(rerank(query,self.retriever.retrieve(query,access_level)),access_level)
        citations=build_citations(chunks[:4])
        answer=self.generator.generate(query,chunks[:4])
        warnings=validate_citations(answer,citations)
        rel,ok,reason=evaluate_answer_relevance(query,answer,citations)
        claims=validate_claims(answer,citations)
        support=sum(c.status=="SUPPORTED" for c in claims)/max(1,len(claims))
        refused=(not ok) or any(c.status in {"UNSUPPORTED","CONTRADICTED"} for c in claims)
        if refused: answer="INSUFFICIENT_EVIDENCE"
        score,label=confidence(min(1,(chunks[0].score/5) if chunks else 0),
                               1 if not warnings else .5,rel,support,refused)
        audit_event("query_completed",refused=refused,confidence=score,claims=len(claims))
        return {"query":query,"answer":answer,
                "citations":[c.__dict__ for c in citations] if not refused else [],
                "confidence":score,"confidence_label":label,"refused":refused,
                "warnings":warnings,"claims":[c.__dict__ for c in claims],
                "debug":{"route":route,"answer_relevance":rel,"answer_relevance_reason":reason,
                         "ranked_chunk_ids":[c.chunk_id for c in chunks]}}

    def refusal(self,query,reason):
        return {"query":query,"answer":"INSUFFICIENT_EVIDENCE","citations":[],
                "confidence":0.0,"confidence_label":"refused","refused":True,
                "warnings":[reason],"claims":[],"debug":{"route":"UNSUPPORTED"}}

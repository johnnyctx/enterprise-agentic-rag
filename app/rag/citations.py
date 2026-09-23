from .models import Citation

def build_citations(chunks):
    return [Citation(f"S{i}",c.chunk_id,c.doc_id,c.title,c.text,c.source_url,
                     c.section,c.retrieval_rank) for i,c in enumerate(chunks,1)]

def validate_citations(answer, citations):
    return [f"Citation {c.span_id} is not referenced by the answer."
            for c in citations if f"[{c.span_id}]" not in answer]

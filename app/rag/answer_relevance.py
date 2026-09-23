import re
STOP = {"what","is","are","the","a","an","to","of","for","on","in","does","do","how","and","or","with","from"}

def terms(text):
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in STOP}

def evaluate_answer_relevance(question, answer, citations):
    if not answer.strip() or "INSUFFICIENT_EVIDENCE" in answer:
        return 0.0, False, "Empty or insufficient answer."
    qt, at = terms(question), terms(answer)
    ev = terms(" ".join(c.text for c in citations))
    lexical = len(qt & at)/max(1,len(qt))
    support = len(at & ev)/max(1,len(at))
    # Require most question-specific terms to survive into the answer. This prevents a
    # well-cited answer about a related topic (e.g. cutoff time) from passing a holiday
    # processing question merely because both share "domestic wires".
    question_focus = len(qt & at) / max(1, len(qt))
    focus = 1.0 if question_focus >= 0.60 else 0.0
    score = .50*lexical + .35*support + .15*focus
    return score, score >= .45, f"question_relevance={lexical:.2f}, evidence_support={support:.2f}"

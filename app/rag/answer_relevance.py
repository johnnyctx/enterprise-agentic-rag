from __future__ import annotations

import re

STOP = {"what", "is", "are", "the", "a", "an", "to", "of", "for", "on", "in", "does", "do", "how", "and", "or", "with", "from"}


def terms(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in STOP}


def evaluate_answer_relevance(question: str, answer: str, citations) -> tuple[float, bool, str]:
    if not answer.strip() or "INSUFFICIENT_EVIDENCE" in answer:
        return 0.0, False, "Empty or insufficient answer."
    qt, at = terms(question), terms(answer)
    ev = terms(" ".join(c.text for c in citations))
    question_focus = len(qt & at) / max(1, len(qt))
    evidence_support = len(at & ev) / max(1, len(at))
    citation_refs = len(re.findall(r"\[S\d+\]", answer))
    citation_factor = min(1.0, citation_refs / max(1, len(re.findall(r"[^.!?]+[.!?]", answer))))
    score = 0.50 * question_focus + 0.35 * evidence_support + 0.15 * citation_factor
    return score, score >= 0.45, f"question_relevance={question_focus:.2f}, evidence_support={evidence_support:.2f}"

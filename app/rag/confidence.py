from __future__ import annotations


def confidence(retrieval: float, citation_integrity: float, answer_relevance: float, claim_support: float, refused: bool):
    if refused:
        return 0.0, "refused"
    score = 0.25 * retrieval + 0.20 * citation_integrity + 0.25 * answer_relevance + 0.30 * claim_support
    label = "high" if score >= 0.75 else "medium" if score >= 0.50 else "low"
    return score, label

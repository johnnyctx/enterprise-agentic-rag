from __future__ import annotations


def confidence(
    retrieval: float,
    citation_integrity: float,
    answer_relevance: float,
    claim_support: float,
    refused: bool,
):
    if refused:
        return 0.0, "refused"

    retrieval = max(0.0, min(1.0, retrieval))
    citation_integrity = max(0.0, min(1.0, citation_integrity))
    answer_relevance = max(0.0, min(1.0, answer_relevance))
    claim_support = max(0.0, min(1.0, claim_support))

    score = (
        0.20 * retrieval
        + 0.15 * citation_integrity
        + 0.35 * answer_relevance
        + 0.30 * claim_support
    )

    # Confidence must not become "high" merely because the answer is well-cited.
    if answer_relevance < 0.45:
        score = min(score, 0.45)
    elif answer_relevance < 0.60:
        score = min(score, 0.59)
    elif answer_relevance < 0.75:
        score = min(score, 0.74)

    if claim_support < 0.50:
        score = min(score, 0.49)
    elif claim_support < 0.70:
        score = min(score, 0.64)
    elif claim_support < 0.85:
        score = min(score, 0.74)

    if citation_integrity < 0.50:
        score = min(score, 0.59)
    elif citation_integrity < 0.70:
        score = min(score, 0.69)

    score = max(0.0, min(1.0, score))
    if score >= 0.75 and answer_relevance >= 0.75:
        label = "high"
    elif score >= 0.50:
        label = "medium"
    else:
        label = "low"
    return score, label

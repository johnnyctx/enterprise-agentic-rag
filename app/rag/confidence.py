def confidence(retrieval, citation_integrity, answer_relevance, claim_support, refused):
    if refused or claim_support < .5 or answer_relevance < .45:
        return 0.0, "refused"
    score=.25*retrieval+.20*citation_integrity+.25*answer_relevance+.30*claim_support
    return score, "high" if score>=.75 else "medium" if score>=.5 else "low"

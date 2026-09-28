from __future__ import annotations

import re

from .models import ClaimValidation

NUMBER = re.compile(r"\b\d+(?:\.\d+)?%?\b")
TIME = re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b", re.I)
MONEY = re.compile(r"\$\s?\d+(?:\.\d+)?")
STOP = {
    "what", "is", "are", "the", "a", "an", "to", "of", "for", "on", "in",
    "does", "do", "how", "and", "or", "with", "from", "that", "this", "these",
    "those", "can", "be", "as", "by", "their", "they", "it", "its", "we", "our",
    "you", "your",
}


def normalized_terms(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOP}


def _normalize_numbers(values: set[str]) -> set[str]:
    return {value.replace(" ", "").lower() for value in values}


def _extract_numbers(text: str) -> set[str]:
    return _normalize_numbers(set(NUMBER.findall(text)))


def _extract_times(text: str) -> set[str]:
    return _normalize_numbers(set(TIME.findall(text)))


def _extract_money(text: str) -> set[str]:
    return _normalize_numbers(set(MONEY.findall(text)))


def extract_claims(answer: str) -> list[str]:
    clean = re.sub(r"\[S\d+\]", "", answer)
    # List numbering is structure, not a factual numeric claim.
    clean = re.sub(r"(?m)^\s*\d+[.)]\s+", "", clean)
    candidates = [
        x.strip(" -•")
        for x in re.split(r"(?<=[.!?])\s+|\n+", clean)
        if x.strip()
    ]
    claims = []
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        if normalized.lower().startswith(("references:", "reference:")):
            continue
        if len(normalized_terms(normalized)) < 4:
            continue
        claims.append(normalized)
    return claims


def _best_evidence_match(claim: str, citations: list) -> tuple[float, list[str]]:
    claim_terms = normalized_terms(claim)
    if not claim_terms:
        return 0.0, []
    best_overlap = 0.0
    best_ids: list[str] = []
    for citation in citations:
        evidence_terms = normalized_terms(citation.text)
        overlap = len(claim_terms & evidence_terms) / len(claim_terms)
        if overlap > best_overlap:
            best_overlap = overlap
            best_ids = [citation.chunk_id]
        elif overlap == best_overlap and overlap > 0:
            best_ids.append(citation.chunk_id)
    return best_overlap, best_ids


def _has_numeric_contradiction(claim: str, evidence_text: str) -> bool:
    claim_nums = _extract_numbers(claim)
    claim_times = _extract_times(claim)
    claim_money = _extract_money(claim)
    evidence_nums = _extract_numbers(evidence_text)
    evidence_times = _extract_times(evidence_text)
    evidence_money = _extract_money(evidence_text)
    # Structural references such as "Appendix 1" are labels, not factual
    # numeric claims. Ignore the appendix number when applying contradiction
    # checks; real quantities, dates, percentages, etc. remain validated.
    numeric_claim_text = re.sub(r"\bappendix\s+\d+\b", "appendix", claim, flags=re.I)
    claim_nums = _extract_numbers(numeric_claim_text)
    if claim_nums and not claim_nums <= evidence_nums:
        return True
    if claim_times and not claim_times <= evidence_times:
        return True
    if claim_money and not claim_money <= evidence_money:
        return True
    return False


def validate_claims(answer: str, citations: list) -> list[ClaimValidation]:
    results: list[ClaimValidation] = []
    claims = extract_claims(answer)
    if not claims:
        return results
    evidence_text = " ".join(citation.text for citation in citations)
    for claim in claims:
        best_overlap, best_ids = _best_evidence_match(claim, citations)
        contradiction = _has_numeric_contradiction(claim, evidence_text)
        if contradiction:
            status = "CONTRADICTED"
            reason = "Numeric, time, or monetary detail is absent from the supplied evidence."
        elif best_overlap >= 0.55:
            status = "SUPPORTED"
            reason = f"Best evidence token overlap={best_overlap:.2f}."
        elif best_overlap >= 0.30:
            status = "PARTIALLY_SUPPORTED"
            reason = f"Best evidence token overlap={best_overlap:.2f}."
        else:
            status = "UNSUPPORTED"
            reason = f"Best evidence token overlap={best_overlap:.2f}."
        results.append(ClaimValidation(claim, status, best_ids, reason))
    return results

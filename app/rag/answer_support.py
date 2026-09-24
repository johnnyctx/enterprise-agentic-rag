from __future__ import annotations

import re

from .models import ClaimValidation

NUMBER = re.compile(r"\b\d+(?:\.\d+)?%?\b")
TIME = re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b", re.I)
MONEY = re.compile(r"\$\s?\d+(?:\.\d+)?")


def extract_claims(answer: str) -> list[str]:
    clean = re.sub(r"\[S\d+\]", "", answer)
    return [x.strip(" -•") for x in re.split(r"(?<=[.!?])\s+|\n+", clean) if x.strip()]


def _normalize_numbers(values: set[str]) -> set[str]:
    return {v.replace(" ", "").lower() for v in values}


def validate_claims(answer: str, citations: list) -> list[ClaimValidation]:
    results: list[ClaimValidation] = []
    for claim in extract_claims(answer):
        claim_terms = set(re.findall(r"[a-z0-9]+", claim.lower()))
        best_overlap = 0.0
        best_ids: list[str] = []
        for citation in citations:
            evidence_terms = set(re.findall(r"[a-z0-9]+", citation.text.lower()))
            overlap = len(claim_terms & evidence_terms) / max(1, len(claim_terms))
            if overlap > best_overlap:
                best_overlap = overlap
                best_ids = [citation.chunk_id]
            elif overlap == best_overlap and overlap > 0:
                best_ids.append(citation.chunk_id)
        claim_nums = _normalize_numbers(set(NUMBER.findall(claim)))
        claim_times = _normalize_numbers(set(TIME.findall(claim)))
        claim_money = _normalize_numbers(set(MONEY.findall(claim)))
        evidence_text = " ".join(c.text for c in citations)
        ev_nums = _normalize_numbers(set(NUMBER.findall(evidence_text)))
        ev_times = _normalize_numbers(set(TIME.findall(evidence_text)))
        ev_money = _normalize_numbers(set(MONEY.findall(evidence_text)))
        contradiction = (
            (claim_nums and not claim_nums <= ev_nums)
            or (claim_times and not claim_times <= ev_times)
            or (claim_money and not claim_money <= ev_money)
        )
        if contradiction:
            status, reason = "CONTRADICTED", "Numeric, time, or monetary detail is absent from evidence."
        elif best_overlap >= 0.55:
            status, reason = "SUPPORTED", f"Best evidence token overlap={best_overlap:.2f}."
        elif best_overlap >= 0.30:
            status, reason = "PARTIALLY_SUPPORTED", f"Best evidence token overlap={best_overlap:.2f}."
        else:
            status, reason = "UNSUPPORTED", f"Best evidence token overlap={best_overlap:.2f}."
        results.append(ClaimValidation(claim, status, best_ids, reason))
    return results

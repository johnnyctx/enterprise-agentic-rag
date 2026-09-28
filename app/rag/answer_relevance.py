from __future__ import annotations

import re

STOP = {
    "what", "is", "are", "the", "a", "an", "to", "of", "for", "on", "in",
    "does", "do", "how", "and", "or", "with", "from", "described", "document",
}

LIST_PATTERNS = (
    r"\bwhat are\b",
    r"\bkey .*principles\b",
    r"\bmain .*principles\b",
    r"\bkey .*steps\b",
    r"\bmain .*steps\b",
    r"\blist\b",
    r"\bidentify\b",
    r"\bwhich .*principles\b",
)


def terms(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in STOP}


def is_list_question(question: str) -> bool:
    return any(re.search(pattern, question.lower()) for pattern in LIST_PATTERNS)


def answer_sentences(answer: str) -> list[str]:
    clean = re.sub(r"\[S\d+\]", "", answer.strip())
    clean = re.sub(r"(?m)^\s*\d+[.)]\s+", "", clean)
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", clean)
        if sentence.strip()
    ]


def citation_count(answer: str) -> int:
    return len(re.findall(r"\[S\d+\]", answer))


def numbered_item_count(answer: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*])\s+", answer))


def substantive_item_count(answer: str) -> int:
    count = 0
    for line in answer.splitlines():
        item = re.sub(r"^\s*(?:\d+[.)]|[-*])\s+", "", line).strip()
        item = re.sub(r"\[S\d+\]", "", item).strip()
        if not item:
            continue
        # A heading-only item is structure, not an answer to a list question.
        if re.fullmatch(r"#{1,6}\s+.+", item):
            continue
        item_terms = terms(item)
        # Short imperative principle labels such as "Minimize costs." are
        # legitimate list items even though they contain only two content terms.
        short_principle = (
            2 <= len(item_terms) <= 10
            and bool(re.search(r"[.!?]$", item))
            and item_terms.intersection({
                "create", "develop", "keep", "minimize", "maintain", "save",
                "invest", "define", "choose", "diversify", "control", "rebalance",
            })
        )
        if short_principle or (len(item_terms) >= 4 and (re.search(r"[.!?]$", item) or len(item_terms) >= 8)):
            count += 1
    return count


def evaluate_answer_relevance(question: str, answer: str, citations) -> tuple[float, bool, str]:
    if not answer.strip() or "INSUFFICIENT_EVIDENCE" in answer:
        return 0.0, False, "Empty or insufficient answer."

    qt, at = terms(question), terms(answer)
    ev = terms(" ".join(c.text for c in citations))
    list_question = is_list_question(question)
    content_qt = qt - {"key", "main", "principles", "list", "identify", "steps"} if list_question else qt
    question_focus = len(content_qt & at) / max(1, len(content_qt))
    evidence_support = len(at & ev) / max(1, len(at))
    sentences = answer_sentences(answer)
    citation_factor = min(1.0, citation_count(answer) / max(1, len(sentences)))

    if list_question:
        items = numbered_item_count(answer)
        substantive_items = substantive_item_count(answer)
        if substantive_items >= 3:
            list_completion = 1.0
        elif substantive_items == 2:
            list_completion = 0.75
        elif substantive_items == 1:
            list_completion = 0.40
        else:
            list_completion = 0.0

        generic_patterns = (
            r"\bdesigned to help\b",
            r"\bprovide a solid framework\b",
            r"\bimprove their chances\b",
            r"\bcan provide\b",
            r"\bis designed to\b",
        )
        generic_hits = sum(bool(re.search(pattern, answer.lower())) for pattern in generic_patterns)
        generic_penalty = 0.30 if generic_hits and substantive_items == 0 else 0.0
        score = (
            0.25 * question_focus
            + 0.25 * evidence_support
            + 0.15 * citation_factor
            + 0.35 * list_completion
            - generic_penalty
        )
        threshold = 0.60
    else:
        score = (
            0.50 * question_focus
            + 0.35 * evidence_support
            + 0.15 * citation_factor
        )
        list_completion = 1.0
        generic_penalty = 0.0
        threshold = 0.45

    score = max(0.0, min(1.0, score))
    reason = (
        f"question_relevance={question_focus:.2f}, "
        f"evidence_support={evidence_support:.2f}, "
        f"citation_factor={citation_factor:.2f}, "
        f"list_question={list_question}, "
        f"list_items={numbered_item_count(answer)}, "
        f"substantive_items={substantive_item_count(answer)}, "
        f"list_completion={list_completion:.2f}, "
        f"generic_penalty={generic_penalty:.2f}"
    )
    return score, score >= threshold, reason

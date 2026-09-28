from __future__ import annotations

import re

from app.rag.models import Chunk

_STOP = {"what", "is", "are", "the", "a", "an", "to", "of", "for", "in", "on", "how", "does", "do", "and", "or", "with", "i", "we", "you"}
_LIST_PATTERNS = (r"\bwhat are\b", r"\bkey .*principles\b", r"\bmain .*principles\b", r"\blist\b", r"\bidentify\b")
_GENERIC_SECTIONS = {"document", "introduction", "conclusion", "references", "reference", "notes on risk", "appendix"}


def _terms(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in _STOP and len(x) > 1}


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]


def _is_list_question(question: str) -> bool:
    q = question.lower()
    return any(re.search(pattern, q) for pattern in _LIST_PATTERNS)


def _is_heading_only(text: str) -> bool:
    """Return True when a chunk contains only a Markdown heading/title."""
    clean = re.sub(r"\s+", " ", text.strip())
    return bool(clean) and bool(re.fullmatch(r"#{1,6}\s+.+", clean))


def _is_substantive(sentence: str) -> bool:
    """Reject headings, labels, and very short fragments as list evidence."""
    clean = re.sub(r"\s+", " ", sentence.strip())
    if not clean or _is_heading_only(clean):
        return False
    if re.fullmatch(r"(?:#{1,6}\s*)?(?:key takeaways|references?|introduction|conclusion|document|appendix(?:\s+\d+)?)[:\-]?", clean, re.I):
        return False
    return len(_terms(clean)) >= 4


class DeterministicLLM:
    """Offline deterministic generator used for repeatable integration tests."""

    def generate(self, question: str, chunks: list[Chunk]) -> str:
        if not chunks:
            return "INSUFFICIENT_EVIDENCE"
        if _is_list_question(question):
            return self._generate_list(question, chunks)
        return self._generate_standard(question, chunks)

    def _generate_standard(self, question: str, chunks: list[Chunk]) -> str:
        q = _terms(question)
        candidates: list[tuple[float, int, str]] = []
        for idx, chunk in enumerate(chunks, 1):
            for sentence in _sentences(chunk.text):
                st = _terms(sentence)
                overlap = len(q & st) / max(1, len(q))
                if overlap:
                    candidates.append((overlap + chunk.score, idx, sentence))
        candidates.sort(reverse=True)
        selected: list[str] = []
        used = set()
        for _, idx, sentence in candidates:
            key = (idx, sentence)
            if key in used:
                continue
            used.add(key)
            selected.append(f"{sentence} [S{idx}]")
            if len(selected) == 3:
                break
        if not selected:
            selected = [f"{_sentences(chunks[0].text)[0]} [S1]"]
        return " ".join(selected)

    def _generate_list(self, question: str, chunks: list[Chunk]) -> str:
        q = _terms(question)
        candidates: list[tuple[float, int, str, str]] = []
        seen_labels: set[str] = set()

        def add_candidate(idx: int, section: str, sentence: str, score: float) -> None:
            clean_sentence = re.sub(r"\s+", " ", sentence.strip())
            clean_section = re.sub(r"\s+", " ", section.strip())
            if not clean_sentence or clean_sentence.lower() in seen_labels:
                return
            candidates.append((score, idx, clean_section, clean_sentence))
            seen_labels.add(clean_sentence.lower())

        for idx, chunk in enumerate(chunks, 1):
            section = re.sub(r"\s+", " ", chunk.section.strip())
            section_lower = section.lower()
            if not section:
                continue
            # Appendix/reference material explains the document; it is not a
            # principle requested by a LIST question. Exclude it before sentence
            # scoring so a high lexical overlap cannot turn it into a list item.
            if re.match(r"^appendix(?:\s+\d+)?\b", section_lower) or re.match(r"^appendix(?:\s+\d+)?\b", re.sub(r"^#{1,6}\s*", "", chunk.text.strip()).lower()):
                continue
            if _is_heading_only(chunk.text):
                # A standalone principle heading can itself be the answer when
                # the PDF extractor separated it from its explanatory paragraph.
                # But a document title is metadata, not a principle. Compare the
                # normalized heading with the chunk's document title so this works
                # for any source document rather than hard-coding Vanguard's title.
                heading = re.sub(r"^#{1,6}\s+", "", chunk.text.strip())
                heading = re.sub(r"^\*\*(.*?)\*\*$", r"\1", heading).strip().rstrip(".")
                normalized_heading = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
                normalized_title = re.sub(r"[^a-z0-9]+", " ", chunk.title.lower()).strip()
                if normalized_heading == normalized_title:
                    continue
                if 2 <= len(_terms(heading)) <= 10 and heading.lower() not in _GENERIC_SECTIONS:
                    add_candidate(idx, "", heading + ".", chunk.score + 0.35)
                continue

            sentences = _sentences(chunk.text)
            # PDF extraction often puts the four principle statements directly
            # in the body rather than preserving their heading hierarchy. Treat
            # a short action-oriented first sentence as the list label and do not
            # replace it with its explanatory paragraph.
            first = sentences[0] if sentences else ""
            first_terms = _terms(first)
            first_verb = next(iter(re.findall(r"[a-z]+", first.lower())), "")
            principle_verbs = {
                "create", "develop", "keep", "minimize", "maintain", "save",
                "invest", "define", "choose", "diversify", "control", "rebalance",
            }
            if (2 <= len(first_terms) <= 10 and first.endswith(".") and first_verb in principle_verbs):
                add_candidate(idx, "", first, chunk.score + 0.80)
                continue

            substantive = [s for s in sentences if _is_substantive(s)]
            if not substantive:
                continue

            section_is_takeaway = section_lower.startswith("key takeaways")
            best_sentence = max(
                substantive,
                key=lambda sentence: len(q & _terms(sentence)) / max(1, len(q)),
            )
            overlap = len(q & _terms(best_sentence)) / max(1, len(q))
            display_section = "" if section_is_takeaway else section
            add_candidate(idx, display_section, best_sentence, chunk.score + overlap + 0.20)

        candidates.sort(reverse=True)
        # Prefer distinct principle labels and cap the answer at the number of
        # substantive principles represented by the evidence.
        selected = candidates[:5]
        if not selected:
            return "INSUFFICIENT_EVIDENCE"
        return "\n".join(
            (f"{rank}. {section}: {sentence} [S{idx}]" if section else f"{rank}. {sentence} [S{idx}]")
            for rank, (_, idx, section, sentence) in enumerate(selected, 1)
        )


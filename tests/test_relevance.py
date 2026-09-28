from app.rag.answer_relevance import evaluate_answer_relevance
from app.rag.models import Citation


def c(text):
    return Citation("S1", "d#1", "d", "Doc", text, "https://example.test", "s", 1)


def test_related_but_wrong_answer_scores_low():
    score, ok, _ = evaluate_answer_relevance(
        "What is the domestic wire cutoff time?",
        "The holiday processing schedule explains market closures. [S1]",
        [c("Domestic wires are subject to holiday processing schedules.")],
    )
    assert score < 0.45
    assert not ok


def test_list_question_requires_multiple_items_for_strong_relevance():
    answer = "1. Create clear investment goals. [S1]"
    score, ok, reason = evaluate_answer_relevance(
        "What are the key principles for investing success?",
        answer,
        [c("Create clear investment goals."), c("Develop a suitable asset allocation."), c("Control costs." )],
    )
    assert score < 0.75
    assert ok is False
    assert "list_completion=0.40" in reason


def test_list_question_rejects_heading_only_items():
    answer = "1. Vanguard's Principles for Investing Success [S1]\n2. Key takeaways about goals [S2]\n3. Key takeaways about balance [S3]"
    score, ok, reason = evaluate_answer_relevance(
        "What are the key principles for investing success?",
        answer,
        [c("Vanguard's Principles for Investing Success"), c("Key takeaways about goals"), c("Key takeaways about balance")],
    )
    assert score < 0.60
    assert ok is False
    assert "substantive_items=0" in reason


def test_list_question_accepts_short_principle_label():
    answer = "1. Minimize costs. [S1]\n2. Maintain perspective and long-term discipline. [S2]\n3. Create clear investment goals. [S3]"
    score, ok, reason = evaluate_answer_relevance(
        "What are the key principles for investing success?",
        answer,
        [c("Minimize costs."), c("Maintain perspective and long-term discipline."), c("Create clear investment goals.")],
    )
    assert ok is True
    assert "substantive_items=3" in reason

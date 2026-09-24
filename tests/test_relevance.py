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

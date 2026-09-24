from app.rag.answer_support import validate_claims
from app.rag.models import Citation


def citation(text):
    return Citation("S1", "d#1", "d", "Doc", text, "https://example.test", "x", 1)


def test_numeric_contradiction():
    result = validate_claims("The cutoff is 5:00 PM ET. [S1]", [citation("Domestic wire cutoff: 4:00 PM ET")])
    assert result[0].status == "CONTRADICTED"


def test_supported_claim():
    result = validate_claims("The cutoff is 4:00 PM ET. [S1]", [citation("Domestic wire cutoff: 4:00 PM ET")])
    assert result[0].status == "SUPPORTED"

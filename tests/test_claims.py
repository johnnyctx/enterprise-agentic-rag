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


def test_appendix_number_is_not_a_numeric_claim():
    from app.rag.answer_support import validate_claims
    from app.rag.models import Citation
    citations = [Citation("S1", "d#1", "d", "Doc", "Appendix 1: Vanguard's Principles for Investing Success is a body of research.", "https://example.test", "Appendix 1", 1)]
    results = validate_claims("Appendix 1: Vanguard's Principles for Investing Success is a body of research. [S1]", citations)
    assert results
    assert results[0].status == "SUPPORTED"

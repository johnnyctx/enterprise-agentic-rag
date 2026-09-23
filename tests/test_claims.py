from app.rag.answer_support import validate_claims
from app.rag.models import Citation

def c(text): return Citation("S1","d#1","d","Doc",text,"url","x",1)

def test_numeric_contradiction():
    r=validate_claims("The cutoff is 5:00 PM ET. [S1]",[c("Domestic wire cutoff: 4:00 PM ET")])
    assert r[0].status=="CONTRADICTED"

def test_supported_claim():
    r=validate_claims("The cutoff is 4:00 PM ET. [S1]",[c("Domestic wire cutoff: 4:00 PM ET")])
    assert r[0].status=="SUPPORTED"

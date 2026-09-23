from app.rag.answer_relevance import evaluate_answer_relevance
from app.rag.models import Citation

def test_wrong_but_well_cited_answer_is_rejected():
    c=Citation("S1","d#1","d","Doc","Domestic wire cutoff: 4:00 PM ET","url","Cutoff",1)
    score,ok,_=evaluate_answer_relevance(
        "What happens to domestic wires submitted on holidays?",
        "Domestic wires have a 4:00 PM ET cutoff. [S1]",[c])
    assert score < .45 and not ok

import re
from .models import ClaimValidation

NUMBER = re.compile(r"\b\d+(?:\.\d+)?%?\b")
TIME = re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b", re.I)
MONEY = re.compile(r"\$\s?\d+(?:\.\d+)?")

def extract_claims(answer):
    clean = re.sub(r"\[[A-Z]\d+\]", "", answer)
    return [x.strip(" -•") for x in re.split(r"(?<=[.!?])\s+|\n+",clean) if x.strip()]

def validate_claims(answer, citations):
    evidence = " ".join(c.text for c in citations)
    ewords = set(re.findall(r"[a-z0-9]+", evidence.lower()))
    en, et, em = set(NUMBER.findall(evidence)), {x.lower().replace(" ","") for x in TIME.findall(evidence)}, set(MONEY.findall(evidence))
    results=[]
    for claim in extract_claims(answer):
        words=set(re.findall(r"[a-z0-9]+",claim.lower()))
        overlap=len(words & ewords)/max(1,len(words))
        nums=set(NUMBER.findall(claim)); times={x.lower().replace(" ","") for x in TIME.findall(claim)}; money=set(MONEY.findall(claim))
        contradiction = (nums and not nums <= en) or (times and not times <= et) or (money and not money <= em)
        if contradiction:
            status, reason="CONTRADICTED","Numeric, time, or monetary detail conflicts with evidence."
        elif overlap >= .35:
            status, reason="SUPPORTED",f"Evidence overlap={overlap:.2f}."
        elif overlap >= .20:
            status, reason="PARTIALLY_SUPPORTED",f"Partial evidence overlap={overlap:.2f}."
        else:
            status, reason="UNSUPPORTED",f"Insufficient evidence overlap={overlap:.2f}."
        results.append(ClaimValidation(claim,status,[c.chunk_id for c in citations],reason))
    return results

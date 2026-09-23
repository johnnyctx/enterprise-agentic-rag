def classify(query):
    q=query.lower()
    if any(x in q for x in ("internal aws","internal architecture","secret")): return "UNSUPPORTED"
    if "privacy" in q or "personal information" in q: return "POLICY"
    if any(x in q for x in ("compare","difference","versus"," vs ")): return "COMPARISON"
    if any(x in q for x in ("how do i","how to","steps","process")): return "PROCEDURAL"
    return "KNOWLEDGE"

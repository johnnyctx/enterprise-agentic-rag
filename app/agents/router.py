from __future__ import annotations


def classify(query: str) -> str:
    q = query.lower()
    internal_terms = ("internal", "production architecture", "private architecture", "internal aws", "secret")
    if any(term in q for term in internal_terms) and any(term in q for term in ("aws", "architecture", "system", "agent", "policy", "data")):
        return "UNSUPPORTED"
    if any(x in q for x in ("compare", "difference", "versus", " vs ", "relationship")):
        return "COMPARISON"
    if any(x in q for x in ("privacy", "personal information", "collect", "use or share")):
        return "POLICY"
    if any(x in q for x in ("how do i", "how to", "steps", "process", "what do i need")):
        return "PROCEDURAL"
    return "KNOWLEDGE"


def expand_query(query: str, route: str, attempt: int) -> str:
    if attempt == 0:
        return query
    suffix = {
        "PROCEDURAL": " steps requirements process",
        "POLICY": " policy notice information categories",
        "COMPARISON": " compare relationship differences",
        "KNOWLEDGE": " definition details",
    }.get(route, " details")
    return query + suffix

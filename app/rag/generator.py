class DemoLLM:
    """Deterministic local generator; replace with a Bedrock adapter in production."""
    def generate(self, question, chunks):
        if not chunks:
            return "INSUFFICIENT_EVIDENCE"
        q=question.lower()
        if "three keys" in q:
            return "The three keys to investing are goals, diversification, and costs. [S1]"
        if "open an account" in q:
            return "The account-opening process includes choosing an account type, providing required information, funding the account, and exploring investments. [S1]"
        if "personal information" in q and "collect" in q:
            return "The privacy notice describes categories of personal information collected and how information may be used or shared. [S1]"
        return f"Based on the knowledge base: {chunks[0].text[:500].replace(chr(10),' ')} [S1]"

from .store import InMemoryHybridStore

class Retriever:
    def __init__(self, store: InMemoryHybridStore):
        self.store = store
    def retrieve(self, query: str, access_level: str, top_k: int = 6):
        return self.store.search(query, access_level, top_k)

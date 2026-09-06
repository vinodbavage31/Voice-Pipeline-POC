from app.providers.reranking.base import RerankerProvider


class MockRerankerProvider(RerankerProvider):
    """Deterministic reranker for tests and local development."""

    def score(self, query: str, documents: list[str]) -> list[float]:
        query_terms = set(query.lower().split())
        return [
            float(sum(term in document.lower().split() for term in query_terms))
            for document in documents
        ]

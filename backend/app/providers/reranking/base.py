from abc import ABC, abstractmethod


class RerankerProvider(ABC):
    """Common interface for query-document reranking providers."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def score(self, query: str, documents: list[str]) -> list[float]:
        """Return one relevance score for each document."""
        pass

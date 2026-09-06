from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Common interface for text embedding providers."""

    def __init__(self, model: str, dimension: int):
        self.model = model
        self.dimension = dimension

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        """Generate one embedding vector for normalized text."""
        pass

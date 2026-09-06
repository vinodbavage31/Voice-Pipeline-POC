from app.providers.embedding.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider for tests and local development."""

    def generate_embedding(self, text: str) -> list[float]:
        normalized_text = " ".join(text.split())
        if not normalized_text:
            raise ValueError("Cannot generate an embedding for empty text")
        seed = sum(ord(character) for character in normalized_text)
        return [float((seed + index) % 100) / 100 for index in range(self.dimension)]

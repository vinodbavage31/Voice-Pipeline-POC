from app.config import settings
from app.providers.embedding.base import EmbeddingProvider


class BGE_M3EmbeddingProvider(EmbeddingProvider):
    """BAAI/bge-m3 embedding provider backed by sentence-transformers."""

    def __init__(
        self,
        model: str | None = None,
        dimension: int | None = None,
    ):
        super().__init__(
            model=model or settings.EMBEDDING_MODEL,
            dimension=dimension or settings.EMBEDDING_DIMENSION,
        )
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for BGE-M3 embeddings."
            ) from exc

        self.encoder = SentenceTransformer(self.model)

    def generate_embedding(self, text: str) -> list[float]:
        normalized_text = " ".join(text.split())
        if not normalized_text:
            raise ValueError("Cannot generate an embedding for empty text")

        vector = self.encoder.encode(normalized_text, normalize_embeddings=True)
        values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        if len(values) != self.dimension:
            raise ValueError(
                f"Embedding model returned {len(values)} dimensions; "
                f"expected {self.dimension}"
            )
        return [float(value) for value in values]

from app.config import settings
from app.providers.reranking.base import RerankerProvider


class CrossEncoderRerankerProvider(RerankerProvider):
    """Cross-encoder reranker backed by sentence-transformers."""

    def __init__(self, model: str | None = None):
        super().__init__(model or settings.RERANKER_MODEL)
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for cross-encoder reranking."
            ) from exc

        self.encoder = CrossEncoder(self.model)

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        pairs = [(query, document) for document in documents]
        scores = self.encoder.predict(pairs)
        values = scores.tolist() if hasattr(scores, "tolist") else list(scores)
        if len(values) != len(documents):
            raise ValueError("Reranker returned an unexpected number of scores")
        return [float(value) for value in values]

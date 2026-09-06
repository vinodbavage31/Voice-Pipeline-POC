from app.config import settings
from app.providers.embedding.base import EmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.EMBEDDING_PROVIDER.lower()
    if provider_name == "bge-m3":
        from app.providers.embedding.bge_m3 import BGE_M3EmbeddingProvider

        return BGE_M3EmbeddingProvider()
    if provider_name == "mock":
        from app.providers.embedding.mock import MockEmbeddingProvider

        return MockEmbeddingProvider(
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
    raise ValueError(f"Unknown embedding provider: {provider_name}")

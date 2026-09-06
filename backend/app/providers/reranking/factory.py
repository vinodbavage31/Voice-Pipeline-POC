from app.config import settings
from app.providers.reranking.base import RerankerProvider


def get_reranker_provider() -> RerankerProvider:
    provider_name = settings.RERANKER_PROVIDER.lower()
    if provider_name == "cross-encoder":
        from app.providers.reranking.cross_encoder import CrossEncoderRerankerProvider

        return CrossEncoderRerankerProvider()
    if provider_name == "mock":
        from app.providers.reranking.mock import MockRerankerProvider

        return MockRerankerProvider(model=settings.RERANKER_MODEL)
    raise ValueError(f"Unknown reranker provider: {provider_name}")

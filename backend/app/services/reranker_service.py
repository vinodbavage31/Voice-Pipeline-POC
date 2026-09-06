from app.providers.reranking.base import RerankerProvider
from app.schemas.search import SearchResult


class RerankerService:
    """Apply an interface-backed reranker to fused retrieval candidates."""

    @staticmethod
    def rerank(
        query: str,
        results: list[SearchResult],
        reranker: RerankerProvider,
        top_k: int = 5,
    ) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")
        if not results:
            return []

        scores = reranker.score(query, [result.content for result in results])
        if len(scores) != len(results):
            raise ValueError("Reranker returned an unexpected number of scores")

        ranked = sorted(
            zip(results, scores),
            key=lambda item: (-item[1], item[0].chunk_id),
        )[:top_k]
        return [
            result.model_copy(update={"score": float(score), "rank": rank})
            for rank, (result, score) in enumerate(ranked, start=1)
        ]

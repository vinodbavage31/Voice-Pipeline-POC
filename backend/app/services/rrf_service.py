from collections.abc import Iterable

from app.schemas.search import SearchResult


class RRFService:
    """Fuse independently ranked result lists with Reciprocal Rank Fusion."""

    DEFAULT_K = 60

    @classmethod
    def fuse(
        cls,
        vector_results: Iterable[SearchResult],
        keyword_results: Iterable[SearchResult],
        top_k: int = 20,
        k: int = DEFAULT_K,
    ) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")
        if k < 1:
            raise ValueError("k must be greater than zero")

        candidates: dict[int, SearchResult] = {}
        scores: dict[int, float] = {}
        for results in (vector_results, keyword_results):
            for result in results:
                candidates.setdefault(result.chunk_id, result)
                scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + (
                    1.0 / (k + result.rank)
                )

        ranked = sorted(
            candidates,
            key=lambda chunk_id: (-scores[chunk_id], chunk_id),
        )[:top_k]
        return [
            candidates[chunk_id].model_copy(
                update={"score": scores[chunk_id], "rank": rank}
            )
            for rank, chunk_id in enumerate(ranked, start=1)
        ]

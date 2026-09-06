from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.providers.embedding.mock import MockEmbeddingProvider
from app.schemas.search import SearchResult
from app.services.reranker_service import RerankerService
from app.services.retrieval_service import RetrievalService
from app.services.rrf_service import RRFService


def make_chunk(chunk_id=7, region="Karnataka"):
    return SimpleNamespace(
        id=chunk_id,
        text="Redacted searchable content.",
        source_type="voice",
        language="en",
        region=region,
        speaker_id="speaker-1",
        audio_id=12,
        chunk_index=0,
        start_time=1.5,
        end_time=4.0,
        asr_model="saaras:v3",
    )


def test_common_result_preserves_chunk_metadata():
    result = RetrievalService._result(make_chunk(), score=0.92, rank=1)

    assert isinstance(result, SearchResult)
    assert result.chunk_id == 7
    assert result.content == "Redacted searchable content."
    assert result.score == 0.92
    assert result.rank == 1
    assert result.metadata == {
        "source_type": "voice",
        "language": "en",
        "region": "Karnataka",
        "speaker_id": "speaker-1",
        "audio_id": 12,
        "chunk_index": 0,
        "start_time": 1.5,
        "end_time": 4.0,
        "asr_model": "saaras:v3",
    }


def test_vector_search_uses_provider_and_returns_ranked_results():
    db = MagicMock()
    query = db.query.return_value
    query.join.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = [(make_chunk(2), 0.1), (make_chunk(3), 0.3)]
    provider = MockEmbeddingProvider(model="mock", dimension=1024)

    results = RetrievalService(provider).vector_search(
        db, "search words", region="Karnataka", top_k=2
    )

    assert [result.chunk_id for result in results] == [2, 3]
    assert [result.rank for result in results] == [1, 2]
    assert [result.score for result in results] == [0.9, 0.7]
    provider_embedding = provider.generate_embedding("search words")
    assert len(provider_embedding) == 1024
    query.limit.assert_called_once_with(2)


def test_keyword_search_returns_ranked_results_and_applies_region():
    db = MagicMock()
    query = db.query.return_value
    query.join.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = [(make_chunk(4), 0.8), (make_chunk(5), 0.2)]

    results = RetrievalService(
        MockEmbeddingProvider(model="mock", dimension=1024)
    ).keyword_search(db, "search words", region="Karnataka", top_k=2)

    assert [result.chunk_id for result in results] == [4, 5]
    assert [result.score for result in results] == [0.8, 0.2]
    assert [result.rank for result in results] == [1, 2]
    query.limit.assert_called_once_with(2)
    assert query.filter.call_count >= 3


def test_rrf_combines_duplicate_results_and_preserves_rank_order():
    vector_results = [
        SearchResult(chunk_id=1, content="one", score=0.9, rank=1, metadata={}),
        SearchResult(chunk_id=2, content="two", score=0.8, rank=2, metadata={}),
    ]
    keyword_results = [
        SearchResult(chunk_id=2, content="two", score=0.7, rank=1, metadata={}),
        SearchResult(chunk_id=3, content="three", score=0.6, rank=2, metadata={}),
    ]

    results = RRFService.fuse(vector_results, keyword_results, top_k=3, k=60)

    assert [result.chunk_id for result in results] == [2, 1, 3]
    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].score == (1 / 62) + (1 / 61)
    assert len(results) == 3


def test_rrf_applies_top_k():
    results = RRFService.fuse(
        [
            SearchResult(chunk_id=1, content="one", score=1, rank=1, metadata={}),
            SearchResult(chunk_id=2, content="two", score=1, rank=2, metadata={}),
        ],
        [],
        top_k=1,
    )

    assert [result.chunk_id for result in results] == [1]


def test_reranker_service_uses_interface_scores():
    results = [
        SearchResult(chunk_id=1, content="first", score=0.1, rank=1, metadata={}),
        SearchResult(chunk_id=2, content="second", score=0.2, rank=2, metadata={}),
    ]
    reranker = MagicMock()
    reranker.score.return_value = [0.2, 0.9]

    reranked = RerankerService.rerank("query", results, reranker, top_k=1)

    assert [result.chunk_id for result in reranked] == [2]
    assert reranked[0].score == 0.9
    assert reranked[0].rank == 1
    reranker.score.assert_called_once_with("query", ["first", "second"])


def test_search_endpoint_returns_dense_and_sparse_results(client: TestClient):
    dense_result = SearchResult(
        chunk_id=1,
        content="Dense result",
        score=0.9,
        rank=1,
        metadata={"region": "Karnataka"},
    )
    sparse_result = SearchResult(
        chunk_id=2,
        content="Keyword result",
        score=0.7,
        rank=1,
        metadata={"region": "Karnataka"},
    )
    retrieval_service = MagicMock()
    retrieval_service.vector_search.return_value = [dense_result]
    retrieval_service.keyword_search.return_value = [sparse_result]
    rrf_result = dense_result.model_copy(update={"score": 0.03, "rank": 1})
    reranked_result = dense_result.model_copy(update={"score": 0.8, "rank": 1})

    with patch("app.api.v1.search.get_embedding_provider"), patch(
        "app.api.v1.search.RetrievalService", return_value=retrieval_service
    ), patch("app.api.v1.search.RRFService.fuse", return_value=[rrf_result]), patch(
        "app.api.v1.search.get_reranker_provider"
    ), patch("app.api.v1.search.RerankerService.rerank", return_value=[reranked_result]):
        response = client.post(
            "/api/v1/search",
            json={"query": "search words", "region": "Karnataka", "top_k": 3},
        )

    assert response.status_code == 200
    assert response.json() == {
        "vector_results": [dense_result.model_dump()],
        "keyword_results": [sparse_result.model_dump()],
        "rrf_results": [rrf_result.model_dump()],
        "reranked_results": [reranked_result.model_dump()],
    }
    assert retrieval_service.vector_search.call_args.kwargs["query"] == "search words"
    assert retrieval_service.vector_search.call_args.kwargs["region"] == "Karnataka"
    assert retrieval_service.vector_search.call_args.kwargs["top_k"] == 20
    assert retrieval_service.keyword_search.call_args.kwargs["top_k"] == 20

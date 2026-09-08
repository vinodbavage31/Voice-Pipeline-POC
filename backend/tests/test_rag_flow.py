import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.search import SearchResult


client = TestClient(app)


def make_result(chunk_id=1, content="evidence text", score=0.9, rank=1):
    return SearchResult(
        chunk_id=chunk_id,
        content=content,
        score=score,
        rank=rank,
        metadata={
            "audio_id": "audio-1",
            "speaker_id": "spk1",
            "region": "Karnataka",
            "start_time": 0.0,
            "end_time": 5.0,
        },
    )


def test_rag_answer_flow():
    # Mock retrieval and reranking to return deterministic evidence
    with patch("app.api.v1.answer.RetrievalService") as mock_retrieval:
        mock_instance = MagicMock()
        mock_instance.vector_search.return_value = [make_result()]
        mock_instance.keyword_search.return_value = []
        mock_retrieval.return_value = mock_instance

        with patch("app.api.v1.answer.RRFService.fuse", return_value=[make_result()]):
            with patch("app.api.v1.answer.get_reranker_provider"):
                with patch("app.api.v1.answer.RerankerService.rerank", return_value=[make_result()]):
                    # Patch generation provider to return an anchored answer
                    fake_gen = MagicMock()
                    fake_gen.generate.return_value = "This is an answer using evidence [1:0.0-5.0]."
                    with patch("app.services.answer_service.get_generation_provider", return_value=fake_gen):
                        payload = {"query": "What happened?", "region": "Karnataka", "top_k": 3}
                        resp = client.post("/api/v1/answer", json=payload)
                        assert resp.status_code == 200
                        data = resp.json()
                        assert "answer" in data
                        assert "citations" in data
                        assert len(data["citations"]) == 1

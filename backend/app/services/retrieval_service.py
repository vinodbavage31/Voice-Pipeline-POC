from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ChunkEmbedding, Transcript, TranscriptChunk, TranscriptType
from app.providers.embedding.base import EmbeddingProvider
from app.schemas.search import SearchResult


class RetrievalService:
    """Independent dense and sparse retrieval over redacted transcript chunks."""

    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider

    def vector_search(
        self,
        db: Session,
        query: str,
        region: Optional[str] = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        query_embedding = self.embedding_provider.generate_embedding(query)
        distance = ChunkEmbedding.embedding.cosine_distance(query_embedding)
        search_query = (
            db.query(TranscriptChunk, distance.label("distance"))
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == TranscriptChunk.id)
            .join(Transcript, Transcript.id == TranscriptChunk.transcript_id)
            .filter(TranscriptChunk.parent_chunk_id.is_not(None))
            .filter(Transcript.transcript_type == TranscriptType.redacted_english)
        )
        if region is not None:
            search_query = search_query.filter(TranscriptChunk.region == region)

        rows = search_query.order_by(distance.asc()).limit(top_k).all()
        return [
            self._result(
                chunk=chunk,
                score=max(0.0, 1.0 - float(distance_value)),
                rank=index,
            )
            for index, (chunk, distance_value) in enumerate(rows, start=1)
        ]

    def keyword_search(
        self,
        db: Session,
        query: str,
        region: Optional[str] = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        document = func.to_tsvector("english", TranscriptChunk.text)
        terms = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank_cd(document, terms)
        search_query = (
            db.query(TranscriptChunk, rank.label("rank_score"))
            .join(Transcript, Transcript.id == TranscriptChunk.transcript_id)
            .filter(TranscriptChunk.parent_chunk_id.is_not(None))
            .filter(Transcript.transcript_type == TranscriptType.redacted_english)
            .filter(document.op("@@")(terms))
        )
        if region is not None:
            search_query = search_query.filter(TranscriptChunk.region == region)

        rows = search_query.order_by(rank.desc()).limit(top_k).all()
        return [
            self._result(
                chunk=chunk,
                score=float(rank_score),
                rank=index,
            )
            for index, (chunk, rank_score) in enumerate(rows, start=1)
        ]

    @staticmethod
    def _result(chunk: TranscriptChunk, score: float, rank: int) -> SearchResult:
        return SearchResult(
            chunk_id=chunk.id,
            content=chunk.text,
            score=score,
            rank=rank,
            metadata={
                "source_type": chunk.source_type,
                "language": chunk.language,
                "region": chunk.region,
                "speaker_id": chunk.speaker_id,
                "audio_id": chunk.audio_id,
                "chunk_index": chunk.chunk_index,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "asr_model": chunk.asr_model,
            },
        )

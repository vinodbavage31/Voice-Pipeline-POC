from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ChunkEmbedding, TranscriptChunk
from app.providers.embedding.base import EmbeddingProvider


class EmbeddingService:
    """Generate and persist embeddings for transcript chunks."""

    @staticmethod
    def store_embedding(
        db: Session,
        chunk: TranscriptChunk,
        embedding: list[float],
        model: str,
    ) -> ChunkEmbedding:
        if len(embedding) != settings.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding has {len(embedding)} dimensions; "
                f"expected {settings.EMBEDDING_DIMENSION}"
            )

        stored_embedding = db.query(ChunkEmbedding).filter(
            ChunkEmbedding.chunk_id == chunk.id
        ).one_or_none()
        if stored_embedding is None:
            stored_embedding = ChunkEmbedding(
                chunk_id=chunk.id,
                embedding=embedding,
                model=model,
                dimension=settings.EMBEDDING_DIMENSION,
            )
            db.add(stored_embedding)
        else:
            stored_embedding.embedding = embedding
            stored_embedding.model = model
            stored_embedding.dimension = settings.EMBEDDING_DIMENSION

        db.flush()
        return stored_embedding

    @classmethod
    def embed_document_chunks(
        cls,
        db: Session,
        chunks: Iterable[TranscriptChunk],
        provider: EmbeddingProvider,
    ) -> list[ChunkEmbedding]:
        stored_embeddings = []
        try:
            for chunk in chunks:
                embedding = provider.generate_embedding(chunk.text)
                stored_embeddings.append(
                    cls.store_embedding(db, chunk, embedding, provider.model)
                )
            db.commit()
        except Exception:
            db.rollback()
            raise

        for stored_embedding in stored_embeddings:
            db.refresh(stored_embedding)
        return stored_embeddings

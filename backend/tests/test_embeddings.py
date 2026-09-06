import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AudioDocument, Transcript, TranscriptChunk, TranscriptType
from app.providers.embedding.bge_m3 import BGE_M3EmbeddingProvider
from app.providers.embedding.factory import get_embedding_provider
from app.providers.embedding.mock import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService


def test_mock_embedding_provider_returns_configured_dimension():
    provider = MockEmbeddingProvider(model="test-model", dimension=4)

    embedding = provider.generate_embedding("  normalized   text ")

    assert len(embedding) == 4
    assert embedding == provider.generate_embedding("normalized text")


def test_bge_m3_provider_uses_configured_model_and_validates_dimension():
    encoder = MagicMock()
    encoder.encode.return_value = [0.1, 0.2, 0.3]
    with patch(
        "app.providers.embedding.bge_m3.settings.EMBEDDING_MODEL", "custom-model"
    ):
        fake_transformers = SimpleNamespace(
            SentenceTransformer=MagicMock(return_value=encoder)
        )
        with patch.dict(sys.modules, {"sentence_transformers": fake_transformers}):
            provider = BGE_M3EmbeddingProvider(model="custom-model", dimension=3)

    assert provider.generate_embedding("  hello   world ") == [0.1, 0.2, 0.3]
    fake_transformers.SentenceTransformer.assert_called_once_with("custom-model")
    encoder.encode.assert_called_once_with(
        "hello world", normalize_embeddings=True
    )


def test_embedding_factory_returns_mock():
    with patch.object(settings, "EMBEDDING_PROVIDER", "mock"), patch.object(
        settings, "EMBEDDING_MODEL", "test-model"
    ), patch.object(settings, "EMBEDDING_DIMENSION", 4):
        provider = get_embedding_provider()

    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.model == "test-model"
    assert provider.dimension == 4


def test_store_embedding_persists_chunk_embedding(db_session: Session):
    audio = AudioDocument(filename="meeting.wav", original_path="meeting.wav")
    db_session.add(audio)
    db_session.flush()
    transcript = Transcript(
        audio_document_id=audio.id,
        transcript_type=TranscriptType.redacted_english,
        text="Redacted transcript.",
    )
    db_session.add(transcript)
    db_session.flush()
    chunk = TranscriptChunk(
        transcript_id=transcript.id,
        text="Redacted transcript.",
        chunk_index=0,
        token_count=2,
        source_type="voice",
        audio_id=audio.id,
    )
    db_session.add(chunk)
    db_session.commit()

    provider = MockEmbeddingProvider(model="test-model", dimension=settings.EMBEDDING_DIMENSION)
    embeddings = EmbeddingService.embed_document_chunks(db_session, [chunk], provider)

    assert len(embeddings) == 1
    stored = db_session.query(embeddings[0].__class__).one()
    assert stored.chunk_id == chunk.id
    assert stored.model == "test-model"
    assert stored.dimension == settings.EMBEDDING_DIMENSION
    assert len(stored.embedding) == settings.EMBEDDING_DIMENSION


def test_embedding_service_rejects_wrong_dimension(db_session: Session):
    chunk = MagicMock()

    with pytest.raises(ValueError, match="dimensions"):
        EmbeddingService.store_embedding(
            db_session,
            chunk,
            [0.1],
            "test-model",
        )

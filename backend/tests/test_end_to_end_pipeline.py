from unittest.mock import MagicMock

from app.db.models import AudioDocument, ChunkEmbedding, Transcript, TranscriptChunk, TranscriptType
from app.providers.embedding.mock import MockEmbeddingProvider
from app.providers.reranking.mock import MockRerankerProvider
from app.providers.translation.mock import MockTranslationProvider
from app.providers.asr.mock import MockASR
from app.services.processing_service import ProcessingService


class FakePIIService:
    def redact(self, text: str, language: str):
        return MagicMock(redacted_text=text.replace("mock", "protected"))


def test_complete_pipeline_with_mocked_external_providers(db_session):
    audio = AudioDocument(
        filename="meeting.wav",
        original_path="/data/uploads/meeting.wav",
        processed_path="/data/processed/meeting.wav",
        region="Karnataka",
        speaker_id="speaker-1",
    )
    db_session.add(audio)
    db_session.commit()

    service = ProcessingService(
        asr_provider=MockASR(model="mock-asr", language="kn-IN"),
        translation_provider=MockTranslationProvider(model_name="mock-translation"),
        embedding_provider=MockEmbeddingProvider(model="mock-embedding", dimension=1024),
        pii_service=FakePIIService(),
    )
    result = service.process_document(db_session, audio)

    assert result.processing_status == "completed"
    assert result.processing_stage == "completed"
    transcripts = db_session.query(Transcript).filter_by(audio_document_id=audio.id).all()
    assert {transcript.transcript_type for transcript in transcripts} == {
        TranscriptType.original,
        TranscriptType.translated_english,
        TranscriptType.redacted_english,
    }
    redacted = next(
        transcript for transcript in transcripts
        if transcript.transcript_type == TranscriptType.redacted_english
    )
    children = db_session.query(TranscriptChunk).filter(
        TranscriptChunk.transcript_id == redacted.id,
        TranscriptChunk.parent_chunk_id.is_not(None),
    ).all()
    assert children
    assert db_session.query(ChunkEmbedding).filter(
        ChunkEmbedding.chunk_id.in_([child.id for child in children])
    ).count() == len(children)

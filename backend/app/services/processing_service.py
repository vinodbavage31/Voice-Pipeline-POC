import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import AudioDocument, Transcript, TranscriptType
from app.observability.tracing import trace_stage
from app.providers.asr.base import ASRProvider
from app.providers.asr.factory import get_asr_provider
from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.factory import get_embedding_provider
from app.providers.translation.base import TranslationProvider
from app.providers.translation.factory import get_translation_provider
from app.services.embedding_service import EmbeddingService
from app.services.pii_service import PIIService
from app.services.transcript_chunking_service import ChunkingService

logger = logging.getLogger(__name__)


class ProcessingService:
    """Run the complete audio-to-searchable-transcript workflow."""

    def __init__(
        self,
        asr_provider: Optional[ASRProvider] = None,
        translation_provider: Optional[TranslationProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        pii_service: Optional[PIIService] = None,
    ):
        self.asr_provider = asr_provider
        self.translation_provider = translation_provider
        self.embedding_provider = embedding_provider
        self.pii_service = pii_service

    def process_document(self, db: Session, audio: AudioDocument) -> AudioDocument:
        try:
            audio.processing_status = "processing"
            audio.processing_error = None
            with trace_stage("audio_processing", {"audio_id": audio.id}):
                self._set_stage(db, audio, "audio_processing")
            asr_provider = self.asr_provider or get_asr_provider()
            translation_provider = self.translation_provider or get_translation_provider()
            embedding_provider = self.embedding_provider or get_embedding_provider()

            with trace_stage("asr", {"audio_id": audio.id}):
                self._set_stage(db, audio, "asr")
                asr_response = asr_provider.transcribe(audio.processed_path)
            original = Transcript(
                audio_document_id=audio.id,
                transcript_type=TranscriptType.original,
                text=asr_response.transcript,
                language=asr_response.language,
                provider=asr_response.provider,
                model=asr_response.model,
                confidence=asr_response.confidence,
                segments=[segment.model_dump() for segment in asr_response.segments],
            )
            db.add(original)
            db.flush()

            with trace_stage("translation", {"audio_id": audio.id, "transcript_id": original.id}):
                self._set_stage(db, audio, "translation")
                translation = translation_provider.translate(
                    asr_response.transcript,
                    asr_response.language,
                    "en",
                )
            translated = Transcript(
                audio_document_id=audio.id,
                transcript_type=TranscriptType.translated_english,
                text=translation.translated_text,
                language=translation.target_language,
                provider=translation.provider,
                model=translation.model,
                confidence=translation.confidence,
                segments=original.segments,
            )
            db.add(translated)
            db.flush()

            with trace_stage("pii", {"audio_id": audio.id, "transcript_id": translated.id}):
                self._set_stage(db, audio, "pii_redaction")
                pii_response = (self.pii_service or PIIService()).redact(
                    translation.translated_text,
                    language="en",
                )
            redacted = Transcript(
                audio_document_id=audio.id,
                transcript_type=TranscriptType.redacted_english,
                text=pii_response.redacted_text,
                language=translation.target_language,
                provider="presidio",
                model="presidio",
                segments=original.segments,
            )
            db.add(redacted)
            db.flush()

            with trace_stage("chunking", {"audio_id": audio.id, "transcript_id": redacted.id}):
                self._set_stage(db, audio, "chunking")
                chunks = ChunkingService.chunk_transcript(db, redacted)

            with trace_stage("embedding", {"audio_id": audio.id, "chunk_count": len(chunks)}):
                self._set_stage(db, audio, "embedding")
                embeddings = EmbeddingService.embed_document_chunks(
                    db, chunks, embedding_provider
                )

            with trace_stage("indexing", {"audio_id": audio.id, "embedding_count": len(embeddings)}):
                self._set_stage(db, audio, "indexing")
            audio.processing_status = "completed"
            audio.processing_stage = "completed"
            db.commit()
            db.refresh(audio)
            return audio
        except Exception as exc:
            logger.exception("Audio processing failed for %s", audio.id)
            audio.processing_status = "failed"
            audio.processing_stage = "failed"
            audio.processing_error = str(exc)[:1000]
            db.commit()
            db.refresh(audio)
            return audio

    @staticmethod
    def _set_stage(db: Session, audio: AudioDocument, stage: str) -> None:
        audio.processing_stage = stage
        db.commit()

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base
from app.config import settings
from pgvector.sqlalchemy import Vector

class AudioDocument(Base):
    __tablename__ = "audio_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True, nullable=False)
    original_path = Column(String, nullable=False)
    processed_path = Column(String, nullable=True)
    
    # Metadata
    duration = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    region = Column(String, nullable=True)
    speaker_id = Column(String, nullable=True)
    processing_status = Column(String, nullable=False, default="uploaded")
    processing_stage = Column(String, nullable=True)
    processing_error = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    transcripts = relationship("Transcript", back_populates="audio_document")

class TranscriptType(str, enum.Enum):
    original = "original" # ASR extracted 
    translated_english = "translated_english"
    redacted_english = "redacted_english"

class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    audio_document_id = Column(Integer, ForeignKey("audio_documents.id"), nullable=False, index=True)
    transcript_type = Column(Enum(TranscriptType), nullable=False)
    text = Column(String, nullable=False)
    
    language = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    
    segments = Column(JSON, nullable=True) # Normalized ASR segments if they exist
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    audio_document = relationship("AudioDocument", back_populates="transcripts")
    chunks = relationship(
        "TranscriptChunk",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptChunk.chunk_index",
    )


class TranscriptChunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_transcript_chunk_index", "transcript_id", "chunk_index"),
    )

    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=False, index=True)
    parent_chunk_id = Column(Integer, ForeignKey("chunks.id"), nullable=True, index=True)
    text = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=False)

    source_type = Column(String, nullable=False, default="voice")
    language = Column(String, nullable=True)
    region = Column(String, nullable=True)
    speaker_id = Column(String, nullable=True)
    audio_id = Column(Integer, ForeignKey("audio_documents.id"), nullable=False, index=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    asr_model = Column(String, nullable=True)

    transcript = relationship("Transcript", back_populates="chunks")
    parent = relationship(
        "TranscriptChunk",
        remote_side=[id],
        back_populates="children",
    )
    children = relationship(
        "TranscriptChunk",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    embedding = relationship(
        "ChunkEmbedding",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(
        Integer,
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    model = Column(String, nullable=False)
    dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunk = relationship("TranscriptChunk", back_populates="embedding")


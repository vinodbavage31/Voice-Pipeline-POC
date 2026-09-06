from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.audio import AudioResponse


class TranscriptResponse(BaseModel):
    id: int
    transcript_type: str
    text: str
    language: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    confidence: Optional[float] = None
    segments: Optional[list[dict[str, Any]]] = None
    created_at: datetime
    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    id: int
    text: str
    chunk_index: int
    token_count: int
    source_type: str
    language: Optional[str] = None
    region: Optional[str] = None
    speaker_id: Optional[str] = None
    audio_id: int
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    asr_model: Optional[str] = None
    parent_chunk_id: Optional[int] = None
    class Config:
        from_attributes = True


class AudioResultResponse(BaseModel):
    audio: AudioResponse
    transcripts: list[TranscriptResponse]
    chunks: list[ChunkResponse]

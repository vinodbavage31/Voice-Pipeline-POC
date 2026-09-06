from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AudioMetadata(BaseModel):
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    language: Optional[str] = None
    region: Optional[str] = None
    speaker_id: Optional[str] = None
    
class AudioResponse(BaseModel):
    id: int
    filename: str
    original_path: str
    processed_path: Optional[str] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    language: Optional[str] = None
    region: Optional[str] = None
    speaker_id: Optional[str] = None
    processing_status: str = "uploaded"
    processing_stage: Optional[str] = None
    processing_error: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

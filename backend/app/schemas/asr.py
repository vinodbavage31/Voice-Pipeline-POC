from pydantic import BaseModel, Field
from typing import List, Optional

class ASRSegment(BaseModel):
    transcript: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class ASRResponse(BaseModel):
    transcript: str
    language: str
    provider: str
    model: str
    confidence: Optional[float] = None
    segments: List[ASRSegment] = Field(default_factory=list)
    request_id: Optional[str] = None

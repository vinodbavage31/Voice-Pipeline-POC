from typing import Any, List, Optional

from pydantic import BaseModel


class Citation(BaseModel):
    audio_id: Optional[int]
    chunk_id: Optional[int]
    content: Optional[str]
    speaker_id: Optional[str]
    region: Optional[str]
    start_time: Optional[float]
    end_time: Optional[float]
    score: Optional[float]
    rank: Optional[int]


class AnswerRequest(BaseModel):
    query: str
    region: Optional[str]
    top_k: int = 5


class AnswerResponse(BaseModel):
    answer: str
    citations: List[Citation]

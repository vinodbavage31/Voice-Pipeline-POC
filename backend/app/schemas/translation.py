from pydantic import BaseModel
from typing import Optional

class TranslationResponse(BaseModel):
    translated_text: str
    provider: str
    model: str
    source_language: str
    target_language: str
    confidence: Optional[float] = None

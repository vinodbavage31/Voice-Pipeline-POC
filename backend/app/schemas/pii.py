from pydantic import BaseModel
from typing import List, Dict, Any

class PIIResponse(BaseModel):
    redacted_text: str
    detected_entities: List[Dict[str, Any]]
    entity_count: int

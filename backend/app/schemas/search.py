from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    region: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: int
    content: str
    score: float
    rank: int
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    vector_results: list[SearchResult]
    keyword_results: list[SearchResult]
    rrf_results: list[SearchResult]
    reranked_results: list[SearchResult]

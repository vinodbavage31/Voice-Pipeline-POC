from typing import List

from app.schemas.search import SearchResult


class ContextBuilder:
    """Builds a grounded context for RAG answer generation from ranked search results."""

    @staticmethod
    def build_context(results: List[SearchResult], max_chars: int = 4000) -> List[dict]:
        """Convert SearchResult list into a list of evidence dicts used as context.

        Keeps results in rank order and truncates the accumulated context to max_chars.
        """
        context = []
        total = 0
        for r in results:
            text = r.content or ""
            entry = {
                "chunk_id": r.chunk_id,
                "content": text,
                "score": r.score,
                "rank": r.rank,
                "metadata": r.metadata or {},
            }
            entry_len = len(text)
            if total + entry_len > max_chars and total > 0:
                break
            context.append(entry)
            total += entry_len
        return context

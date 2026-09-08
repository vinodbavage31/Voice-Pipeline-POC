import logging
from typing import List

from app.providers.generation.factory import get_generation_provider
from app.services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class AnswerService:
    """Builds grounded answers using retrieved evidence and a generation provider."""

    def __init__(self):
        self.generator = get_generation_provider()

    def build_prompt(self, question: str, context: List[dict]) -> str:
        parts = [
            "You are an assistant that MUST answer only using the provided evidence. If the answer is not present, say 'I don't know'.",
            f"Question: {question}",
            "Evidence:",
        ]
        for i, e in enumerate(context, start=1):
            meta = e.get("metadata", {})
            parts.append("---")
            parts.append(f"[{i}] chunk_id={e.get('chunk_id')} score={e.get('score')} rank={e.get('rank')}")
            parts.append(f"source: {meta.get('audio_id')} speaker: {meta.get('speaker_id')} region: {meta.get('region')}")
            parts.append(e.get("content", ""))

        parts.append("\nInstructions: Answer concisely using only the Evidence above. For each claim, include a citation in the form [chunk_id:start-end].")
        return "\n".join(parts)

    def generate_answer(self, question: str, reranked_results: List[dict]) -> dict:
        context = ContextBuilder.build_context(reranked_results)
        prompt = self.build_prompt(question, context)
        logger.debug("Generated prompt with %d context entries", len(context))
        text = self.generator.generate(prompt)

        # Build citation objects from used context — here we conservatively include all context items
        citations = []
        for e in context:
            meta = e.get("metadata", {})
            citations.append(
                {
                    "audio_id": meta.get("audio_id"),
                    "chunk_id": e.get("chunk_id"),
                    "content": e.get("content"),
                    "speaker_id": meta.get("speaker_id"),
                    "region": meta.get("region"),
                    "start_time": meta.get("start_time"),
                    "end_time": meta.get("end_time"),
                    "score": e.get("score"),
                    "rank": e.get("rank"),
                }
            )

        return {"answer": text, "citations": citations}

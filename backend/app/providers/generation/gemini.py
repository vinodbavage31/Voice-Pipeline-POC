import logging
from app.providers.generation.base import GenerationProvider

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class GeminiGenerationProvider(GenerationProvider):
    """Simple Gemini-backed generation provider for grounded answers."""

    def __init__(self, model_name: str, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided for generation")
        if genai is None:
            raise ImportError("google-generativeai package is required for Gemini generation")
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        try:
            resp = self.model.generate_content(prompt)
            text = resp.text if resp and getattr(resp, "text", None) else ""
            return text.strip()
        except Exception as e:
            logger.exception("Gemini generation failed: %s", e)
            raise

import logging
from app.providers.translation.base import TranslationProvider
from app.schemas.translation import TranslationResponse

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

class GeminiTranslationProvider(TranslationProvider):
    """
    Google Gemini implementation for highly constrained translation.
    """
    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name)
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided")
        if genai is None:
            raise ImportError("google-generativeai package is required.")
        
        self.api_key = api_key
        # Configure the genai SDK. Ideally, this should be done once on app startup,
        # but for scoping this is acceptable.
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResponse:
        prompt = f"""
Translate the following text from {source_lang} to {target_lang}.
Strict Guidelines:
1. Preserve the exact original meaning.
2. Preserve all names, places, numbers, and dates as they appear.
3. Preserve domain-specific terminology.
4. Do NOT summarize or shorten the text.
5. Do NOT invent, hallucinate, or add any information outside of the given text.

Text to Translate:
{text}
"""
        try:
            # We enforce a timeout natively or implicitly if the API provides one
            response = self.model.generate_content(prompt)
            if not response or not response.text:
                raise ValueError("Received empty response from Gemini API.")
                
            return TranslationResponse(
                translated_text=response.text.strip(),
                provider="gemini",
                model=self.model_name,
                source_language=source_lang,
                target_language=target_lang,
                confidence=None
            )
        except Exception as e:
            logger.error(f"Gemini API Translation Error: {e}")
            raise Exception(f"Translation failed: {str(e)}")

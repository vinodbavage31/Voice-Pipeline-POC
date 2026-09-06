import time
from app.providers.translation.base import TranslationProvider
from app.schemas.translation import TranslationResponse

class MockTranslationProvider(TranslationProvider):
    """
    Mock Translation Provider for testing.
    """
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResponse:
        # Simulate network latency
        time.sleep(0.1)
        
        return TranslationResponse(
            translated_text=f"[Mock Translated from {source_lang} to {target_lang}]: {text}",
            provider="mock",
            model=self.model_name,
            source_language=source_lang,
            target_language=target_lang,
            confidence=1.0
        )

from app.config import settings
from app.providers.translation.base import TranslationProvider

def get_translation_provider() -> TranslationProvider:
    provider_name = settings.TRANSLATION_PROVIDER.lower()
    
    # We default GEMINI model to gemini-3.6-flash if not specified elsewhere. 
    # Usually you'd configure this in app/config.py, let's just use a hardcoded fallback.
    gemini_model_name = "gemini-3.6-flash"
    
    if provider_name == "gemini":
        from app.providers.translation.gemini import GeminiTranslationProvider
        return GeminiTranslationProvider(
            model_name=gemini_model_name,
            api_key=settings.GEMINI_API_KEY
        )
    elif provider_name == "mock":
        from app.providers.translation.mock import MockTranslationProvider
        return MockTranslationProvider(model_name="mock-model")
    else:
        raise ValueError(f"Unknown Translation provider: {provider_name}")

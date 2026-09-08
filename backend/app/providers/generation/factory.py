from app.config import settings


def get_generation_provider():
    provider_name = getattr(settings, "GENERATION_PROVIDER", "gemini").lower()
    if provider_name == "gemini":
        from app.providers.generation.gemini import GeminiGenerationProvider

        return GeminiGenerationProvider(model_name=getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash"), api_key=settings.GEMINI_API_KEY)

    raise ValueError(f"Unknown generation provider: {provider_name}")

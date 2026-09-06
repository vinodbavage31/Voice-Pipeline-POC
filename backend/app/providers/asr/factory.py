from app.config import settings
from app.providers.asr.base import ASRProvider

def get_asr_provider() -> ASRProvider:
    """
    Factory function to get the configured ASR provider instance.
    """
    provider_name = settings.ASR_PROVIDER.lower()
    
    if provider_name == "sarvam":
        from app.providers.asr.sarvam import SarvamASR
        return SarvamASR(
            model=settings.ASR_MODEL, 
            language=settings.ASR_LANGUAGE, 
            api_key=settings.SARVAM_API_KEY
        )
    elif provider_name == "mock":
        from app.providers.asr.mock import MockASR
        return MockASR(
            model=settings.ASR_MODEL,
            language=settings.ASR_LANGUAGE
        )
    else:
        raise ValueError(f"Unknown ASR provider: {provider_name}")

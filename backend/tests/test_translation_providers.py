import pytest
import os
from unittest.mock import patch
from app.providers.translation.factory import get_translation_provider
from app.providers.translation.mock import MockTranslationProvider
from app.providers.translation.gemini import GeminiTranslationProvider
from app.schemas.translation import TranslationResponse

@pytest.fixture(autouse=True)
def mock_env_vars():
    # Make sure we don't accidentally use a real API key in tests
    with patch.dict(os.environ, {
        "TRANSLATION_PROVIDER": "mock",
        "GEMINI_API_KEY": "fake_gemini_key"
    }, clear=True):
        from app.config import settings
        # We also need to patch settings directly because it's already instantiated
        settings.TRANSLATION_PROVIDER = "mock"
        settings.GEMINI_API_KEY = "fake_gemini_key"
        yield

def test_mock_translation_provider():
    provider = MockTranslationProvider(model_name="mock-model")
    response = provider.translate(text="Namaskara", source_lang="kn-IN", target_lang="en-US")
    
    assert isinstance(response, TranslationResponse)
    assert response.provider == "mock"
    assert response.source_language == "kn-IN"
    assert response.target_language == "en-US"
    assert "Namaskara" in response.translated_text
    assert "mock-model" == response.model

def test_factory_returns_mock():
    # settings are overriden to 'mock' by fixture
    provider = get_translation_provider()
    assert isinstance(provider, MockTranslationProvider)
    
def test_factory_returns_gemini():
    with patch("app.config.settings.TRANSLATION_PROVIDER", "gemini"):
        with patch("app.config.settings.GEMINI_API_KEY", "dummy_key"):
            with patch("app.providers.translation.gemini.genai.configure"):
                with patch("app.providers.translation.gemini.genai.GenerativeModel"):
                    provider = get_translation_provider()
                    assert isinstance(provider, GeminiTranslationProvider)
                    assert provider.model_name == "gemini-pro"

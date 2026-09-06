import pytest
import os
from unittest.mock import patch
from app.providers.asr.factory import get_asr_provider
from app.providers.asr.mock import MockASR
from app.providers.asr.sarvam import SarvamASR
from app.schemas.asr import ASRResponse

@pytest.fixture(autouse=True)
def mock_env_vars():
    # Make sure we don't accidentally use a real API key in tests
    with patch.dict(os.environ, {
        "ASR_PROVIDER": "mock",
        "ASR_MODEL": "test_model",
        "ASR_LANGUAGE": "en-US",
        "SARVAM_API_KEY": "fake_key"
    }, clear=True):
        from app.config import settings
        # We also need to patch settings directly because it's already instantiated
        settings.ASR_PROVIDER = "mock"
        settings.ASR_MODEL = "test_model"
        settings.ASR_LANGUAGE = "en-US"
        settings.SARVAM_API_KEY = "fake_key"
        yield

def test_mock_asr_provider():
    provider = MockASR(model="test_model", language="en-US")
    response = provider.transcribe("fake_path.wav")
    
    assert isinstance(response, ASRResponse)
    assert response.provider == "mock"
    assert response.model == "test_model"
    assert response.language == "en-US"
    assert response.transcript == "This is a mock transcription for testing."
    assert len(response.segments) == 2

def test_factory_returns_mock():
    # settings are overriden to 'mock' by fixture
    provider = get_asr_provider()
    assert isinstance(provider, MockASR)
    
def test_factory_returns_sarvam():
    with patch("app.config.settings.ASR_PROVIDER", "sarvam"):
        with patch("app.config.settings.ASR_MODEL", "saaras_test"):
            with patch("app.config.settings.SARVAM_API_KEY", "dummy_key"):
                with patch("app.providers.asr.sarvam.SarvamAI"):
                    provider = get_asr_provider()
                    assert isinstance(provider, SarvamASR)
                    assert provider.model == "saaras_test"

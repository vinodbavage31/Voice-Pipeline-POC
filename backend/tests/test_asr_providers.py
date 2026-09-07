import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

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


def test_sarvam_transcribe_short_audio_uses_direct_api():
    provider = SarvamASR(model="saaras:v3", language="en-IN", api_key="fake_key")
    provider.client = MagicMock()
    provider.client.speech_to_text.transcribe.return_value = SimpleNamespace(
        transcript="hello world",
        request_id="req-123",
    )

    with patch("app.providers.asr.sarvam.FFmpegService.extract_metadata", return_value={"duration": 12.0}):
        with patch("builtins.open", create=True) as mock_open:
            response = provider.transcribe("/tmp/test.wav")

    assert isinstance(response, ASRResponse)
    assert response.transcript == "hello world"
    assert response.request_id == "req-123"
    provider.client.speech_to_text.transcribe.assert_called_once()


def test_sarvam_transcribe_long_audio_uses_batch_job():
    provider = SarvamASR(model="saaras:v3", language="en-IN", api_key="fake_key")
    provider.client = MagicMock()

    batch_job = MagicMock()
    batch_job.job_id = "job-456"
    batch_job.upload_files.return_value = True
    batch_job.start.return_value = SimpleNamespace(job_state="Processing")
    batch_job.wait_until_complete.return_value = SimpleNamespace(job_state="Completed")
    batch_job.get_file_results.return_value = {
        "successful": [{"file_name": "test.wav", "output_file": "0.json"}],
        "failed": [],
    }

    provider.client.speech_to_text_job.create_job.return_value = batch_job
    provider.client.speech_to_text_job.get_download_links.return_value = SimpleNamespace(
        download_urls={"0.json": SimpleNamespace(file_url="https://example.test/download?se=2026-09-07T15%253A22%253A23Z&sig=abc%252Bdef")}
    )

    with patch("app.providers.asr.sarvam.FFmpegService.extract_metadata", return_value={"duration": 45.0}):
        with patch("app.providers.asr.sarvam.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = (
                b'{"transcript": "This is a long-form transcript.", '
                b'"timestamps": {"segments": [{"text": "This is a long-form transcript.", "start": 0.0, "end": 8.0}]}}'
            )
            mock_get.return_value = mock_response

            response = provider.transcribe("/tmp/test.wav")

    assert response.transcript == "This is a long-form transcript."
    assert response.provider == "sarvam"
    assert response.model == "saaras:v3"
    assert response.segments[0].transcript == "This is a long-form transcript."
    provider.client.speech_to_text_job.create_job.assert_called_once()
    batch_job.upload_files.assert_called_once_with(["/tmp/test.wav"])
    batch_job.start.assert_called_once_with()
    batch_job.download_outputs.assert_not_called()
    provider.client.speech_to_text_job.get_download_links.assert_called_once_with(
        job_id="job-456",
        files=["0.json"],
    )
    mock_get.assert_called_once_with(
        "https://example.test/download?se=2026-09-07T15%253A22%253A23Z&sig=abc%252Bdef",
        follow_redirects=True,
        timeout=60.0,
    )

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import io
import json

def test_validation_unsupported_file(client: TestClient):
    # Trying to upload a completely unsupported file
    file_content = b"fake data"
    response = client.post(
        "/api/v1/audio/upload",
        files={"file": ("test.txt", file_content, "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

@patch("app.services.audio_service.FFmpegService")
def test_audio_upload_success(mock_ffmpeg, client: TestClient):
    # Mock FFmpegService
    mock_ffmpeg.extract_metadata.return_value = {
        "duration": 5.0,
        "sample_rate": 44100,
        "channels": 2
    }
    mock_ffmpeg.process_to_asr_format.return_value = "processed.wav"

    # Create dummy audio file
    file_content = b"fake audio data"
    response = client.post(
        "/api/v1/audio/upload",
        files={"file": ("test.mp3", file_content, "audio/mpeg")},
        data={"language": "en-US", "speaker_id": "spk-123"}
    )
    
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["filename"] == "test.mp3"
    assert data["duration"] == 5.0
    assert data["sample_rate"] == 44100
    assert data["channels"] == 2
    assert data["language"] == "en-US"
    assert data["speaker_id"] == "spk-123"
    assert data["processed_path"].endswith("_processed.wav")
    assert "id" in data

    # Test GET endpoint
    audio_id = data["id"]
    get_response = client.get(f"/api/v1/audio/{audio_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == audio_id

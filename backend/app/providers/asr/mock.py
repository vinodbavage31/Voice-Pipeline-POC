import uuid
import time
from app.providers.asr.base import ASRProvider
from app.schemas.asr import ASRResponse, ASRSegment

class MockASR(ASRProvider):
    """
    Mock ASR Provider for testing and local development without incurring API costs.
    """
    def __init__(self, model: str, language: str):
        super().__init__(model, language)

    def transcribe(self, file_path: str) -> ASRResponse:
        # Simulate network delay securely
        time.sleep(0.1)
        
        # Return a deterministic mock response
        return ASRResponse(
            transcript="This is a mock transcription for testing.",
            language=self.language,
            provider="mock",
            model=self.model,
            confidence=0.99,
            segments=[
                ASRSegment(
                    transcript="This is a mock",
                    start_time=0.0,
                    end_time=1.5
                ),
                ASRSegment(
                    transcript="transcription for testing.",
                    start_time=1.5,
                    end_time=3.0
                )
            ],
            request_id=str(uuid.uuid4())
        )

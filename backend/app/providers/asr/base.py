from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.asr import ASRResponse
import warnings

class ASRProvider(ABC):
    """
    Abstract base class for all ASR Providers.
    """
    def __init__(self, model: str, language: str):
        self.model = model
        self.language = language

    @abstractmethod
    def transcribe(self, file_path: str) -> ASRResponse:
        """
        Transcribes the given audio file and returns a normalized ASRResponse.
        
        Args:
            file_path: Absolute path to the audio file to transcribe.
            
        Returns:
            ASRResponse: The normalized transcription result.
            
        Raises:
            Exception: If there's an error calling the ASR service.
        """
        pass

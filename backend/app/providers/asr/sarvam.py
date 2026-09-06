from app.providers.asr.base import ASRProvider
from app.schemas.asr import ASRResponse, ASRSegment

try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None

class SarvamASR(ASRProvider):
    """
    ASR implementation for Sarvam AI.
    """
    def __init__(self, model: str, language: str, api_key: str):
        super().__init__(model, language)
        if not api_key:
            raise ValueError("SARVAM_API_KEY must be provided")
        if SarvamAI is None:
            raise ImportError("sarvamai package is required. Install it using 'pip install sarvamai'")
        
        self.api_key = api_key
        # For simplicity we construct it directly, this could be configured with a timeout wrapper
        self.client = SarvamAI(api_subscription_key=self.api_key)
        
    def transcribe(self, file_path: str) -> ASRResponse:
        try:
            with open(file_path, "rb") as f:
                response = self.client.speech_to_text.transcribe(
                    file=f,
                    model=self.model,
                    mode="transcribe",
                    language_code=self.language
                )
            
            # The SDK object structure depends heavily on what sarvamai returns
            # Example mapping; normally we map segments if supported.
            transcript = getattr(response, "transcript", "")
            
            # Request ID or confidence could be missing depending on response format.
            request_id = getattr(response, "request_id", None)
            
            return ASRResponse(
                transcript=transcript,
                language=self.language,
                provider="sarvam",
                model=self.model,
                confidence=None,  # Adjust when sarvam sdk confidence format is known
                segments=[],      # Populated when word or segment timestamps are available
                request_id=request_id
            )
        except Exception as e:
            raise Exception(f"Sarvam AI API failed: {str(e)}")

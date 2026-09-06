from abc import ABC, abstractmethod
from app.schemas.translation import TranslationResponse

class TranslationProvider(ABC):
    """
    Abstract base class for all Text Translation Providers.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResponse:
        """
        Translates text with specific constraints.
        
        Args:
            text: The text to translate.
            source_lang: The language to translate from.
            target_lang: The language to translate to.
            
        Returns:
            TranslationResponse: The resulting translated text and metadata.
            
        Raises:
            Exception: If translation fails.
        """
        pass

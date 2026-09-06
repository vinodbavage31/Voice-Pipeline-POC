import logging
from typing import List
from app.schemas.pii import PIIResponse

try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
except ImportError:
    AnalyzerEngine = None
    PatternRecognizer = None
    Pattern = None
    AnonymizerEngine = None
    OperatorConfig = None

logger = logging.getLogger(__name__)

class PIIService:
    def __init__(self):
        if AnalyzerEngine is None:
            raise ImportError("Presidio is not installed.")
        
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        self._add_custom_recognizers()
        
    def _add_custom_recognizers(self):
        # Indian PAN Format: 5 letters, 4 digits, 1 letter
        pan_pattern = Pattern(
            name="pan_pattern",
            regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
            score=0.8
        )
        pan_recognizer = PatternRecognizer(
            supported_entity="IN_PAN",
            patterns=[pan_pattern],
            context=["pan", "tax", "income tax"]
        )
        
        # Aadhaar Format: 12 digits, often with spaces
        aadhaar_pattern = Pattern(
            name="aadhaar_pattern",
            regex=r"\b\d{4}\s?\d{4}\s?\d{4}\b",
            score=0.8
        )
        aadhaar_recognizer = PatternRecognizer(
            supported_entity="IN_AADHAAR",
            patterns=[aadhaar_pattern],
            context=["aadhaar", "uidai", "id"]
        )
        
        self.analyzer.registry.add_recognizer(pan_recognizer)
        self.analyzer.registry.add_recognizer(aadhaar_recognizer)
        
    def redact(self, text: str, language: str = "en") -> PIIResponse:
        """
        Detects and redact PII content from the input text.
        We filter specific built-in entities along with custom IN_PAN and IN_AADHAAR.
        We use a high score threshold to avoid redacting domain terminology blindly.
        """
        entities_to_detect = [
            "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION", "DATE_TIME",
            "IN_PAN", "IN_AADHAAR"
        ]
        
        try:
            results = self.analyzer.analyze(
                text=text, 
                language=language, 
                entities=entities_to_detect,
                score_threshold=0.6  # Adjust based on sensitivity
            )
            
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results
            )
            
            detected_entities = [
                {
                    "entity_type": res.entity_type,
                    "start": res.start,
                    "end": res.end,
                    "score": res.score
                }
                for res in results
            ]
            
            return PIIResponse(
                redacted_text=anonymized_result.text,
                detected_entities=detected_entities,
                entity_count=len(results)
            )
        except Exception as e:
            logger.error(f"PII Redaction error: {e}")
            raise Exception("Failed to redact text.")

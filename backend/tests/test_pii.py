import pytest
from app.services.pii_service import PIIService

@pytest.fixture(scope="module")
def pii_service():
    # Only load it if presidio is installed correctly in the container
    try:
        service = PIIService()
        yield service
    except ImportError:
        pytest.skip("Presidio not installed")

def test_redact_person(pii_service):
    text = "My name is John Doe."
    response = pii_service.redact(text)
    assert "John Doe" not in response.redacted_text
    assert "<PERSON>" in response.redacted_text
    assert response.entity_count >= 1
    
def test_redact_email(pii_service):
    text = "Contact me at fake@email.com for details."
    response = pii_service.redact(text)
    assert "fake@email.com" not in response.redacted_text
    assert "<EMAIL_ADDRESS>" in response.redacted_text
    assert response.entity_count >= 1
    
def test_redact_indian_pan(pii_service):
    text = "His PAN is ABCDE1234F."
    response = pii_service.redact(text)
    assert "ABCDE1234F" not in response.redacted_text
    assert "<IN_PAN>" in response.redacted_text
    assert response.entity_count >= 1
    
def test_redact_aadhaar(pii_service):
    # Note: Presidio may also detect DATE_TIME on digit sequences, so we check >= 1
    text = "My Aadhaar id is 1234 5678 9012"
    response = pii_service.redact(text)
    # The original 12-digit number must not appear verbatim in output
    assert "1234 5678 9012" not in response.redacted_text
    # At least one entity must be IN_AADHAAR
    entity_types = [e["entity_type"] for e in response.detected_entities]
    assert "IN_AADHAAR" in entity_types
    assert response.entity_count >= 1

def test_do_not_redact_domain_terminology(pii_service):
    text = "The system uses vector databases for RAG."
    response = pii_service.redact(text)
    # Shouldn't redact normal words blindly
    assert "vector databases" in response.redacted_text
    assert response.entity_count == 0

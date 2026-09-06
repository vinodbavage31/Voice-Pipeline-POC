from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.audio import AudioResponse
from app.schemas.pipeline import AudioResultResponse
from app.services.audio_service import AudioService
from app.services.processing_service import ProcessingService

router = APIRouter(prefix="/api/v1/audio", tags=["Audio Ingestion"])

@router.post("/upload", response_model=AudioResponse)
def upload_audio(
    file: UploadFile = File(...),
    language: str = Form(None),
    region: str = Form(None),
    speaker_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload an audio file, extract metadata, preprocess it to WAV mono 16kHz,
    and save the document to the database.
    """
    document = AudioService.process_upload(
        db=db, 
        file=file, 
        language=language, 
        region=region, 
        speaker_id=speaker_id
    )
    return ProcessingService().process_document(db=db, audio=document)

@router.get("/{audio_id}/status", response_model=AudioResponse)
def get_audio_status(audio_id: int, db: Session = Depends(get_db)):
    return AudioService.get_audio(db=db, audio_id=audio_id)

@router.get("/{audio_id}/result", response_model=AudioResultResponse)
def get_audio_result(audio_id: int, db: Session = Depends(get_db)):
    document = AudioService.get_audio(db=db, audio_id=audio_id)
    redacted_transcript = next(
        (
            transcript
            for transcript in document.transcripts
            if transcript.transcript_type.value == "redacted_english"
        ),
        None,
    )
    chunks = redacted_transcript.chunks if redacted_transcript else []
    return AudioResultResponse(
        audio=document,
        transcripts=document.transcripts,
        chunks=[chunk for chunk in chunks if chunk.parent_chunk_id is not None],
    )

@router.get("/{audio_id}", response_model=AudioResponse)
def get_audio(audio_id: int, db: Session = Depends(get_db)):
    """
    Get information about a specific audio document by ID
    """
    return AudioService.get_audio(db=db, audio_id=audio_id)

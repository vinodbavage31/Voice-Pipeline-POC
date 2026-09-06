import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.db.models import AudioDocument
from app.config import settings
from app.observability.tracing import trace_stage
from app.services.ffmpeg_service import FFmpegService

class AudioService:
    @staticmethod
    def process_upload(db: Session, file: UploadFile, language: str = None, region: str = None, speaker_id: str = None) -> AudioDocument:
        # Validate format (basic extension/content type check via config)
        # Note: robust validation could rely on python-magic, but we'll use content type here
        valid_extensions = [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in valid_extensions:
            raise HTTPException(status_code=400, detail=f"Unsupported file format. Supported: {', '.join(valid_extensions)}")
            
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
        
        # Save original file
        file_id = str(uuid.uuid4())
        original_filename = f"{file_id}{file_ext}"
        original_path = os.path.join(settings.UPLOAD_DIR, original_filename)
        
        try:
            with open(original_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to write uploaded file.")
            
        with trace_stage("audio_processing", {"filename": file.filename}):
            # Extract metadata
            try:
                metadata = FFmpegService.extract_metadata(original_path)
            except Exception as e:
                # Fallback if ffprobe fails
                metadata = {"duration": None, "sample_rate": None, "channels": None}

            # Preprocess Audio
            processed_filename = f"{file_id}_processed.wav"
            processed_path = os.path.join(settings.PROCESSED_DIR, processed_filename)
            try:
                FFmpegService.process_to_asr_format(original_path, processed_path)
            except Exception as e:
                # We can still save the document if preprocessing fails, but usually we want to fail
                raise HTTPException(status_code=500, detail="Audio preprocessing failed.")
            
        # Create DB record
        db_document = AudioDocument(
            filename=file.filename,
            original_path=original_path,
            processed_path=processed_path,
            duration=metadata.get("duration"),
            sample_rate=metadata.get("sample_rate"),
            channels=metadata.get("channels"),
            language=language,
            region=region,
            speaker_id=speaker_id
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return db_document
        
    @staticmethod
    def get_audio(db: Session, audio_id: int) -> AudioDocument:
        audio = db.query(AudioDocument).filter(AudioDocument.id == audio_id).first()
        if not audio:
            raise HTTPException(status_code=404, detail="Audio document not found")
        return audio

from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Voice RAG Prototype"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/voicedb")
    # Base directory for storage mapped from docker-compose /app/data
    DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")
    
    # Audio upload configurations
    UPLOAD_DIR: str = os.path.join(DATA_DIR, "uploads")
    PROCESSED_DIR: str = os.path.join(DATA_DIR, "processed")
    ALLOWED_AUDIO_TYPES: list[str] = ["audio/wav", "audio/mpeg", "audio/x-m4a", "audio/flac", "audio/ogg", "audio/webm", "video/webm"]

    # ASR settings
    ASR_PROVIDER: str = os.getenv("ASR_PROVIDER", "sarvam") # e.g 'sarvam' or 'mock'
    ASR_MODEL: str = os.getenv("ASR_MODEL", "saaras:v3")
    ASR_LANGUAGE: str = os.getenv("ASR_LANGUAGE", "kn-IN")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")

    # Translation settings
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Embedding settings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "bge-m3")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # Retrieval fusion and reranking settings
    RRF_K: int = int(os.getenv("RRF_K", "60"))
    RRF_TOP_K: int = int(os.getenv("RRF_TOP_K", "20"))
    RERANKER_PROVIDER: str = os.getenv("RERANKER_PROVIDER", "cross-encoder")
    RERANKER_MODEL: str = os.getenv(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # Observability settings
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    class Config:
        env_file = ".env"

settings = Settings()

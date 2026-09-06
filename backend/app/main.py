from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db, Base, engine
from app.db import models

# Ensure tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Voice RAG Prototype API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1 import audio, search
app.include_router(audio.router)
app.include_router(search.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Check DB Connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok",
        "database": db_status
    }

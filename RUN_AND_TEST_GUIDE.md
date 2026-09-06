# Voice RAG Prototype: Run and Test Guide

_Last updated: 2026-09-03_

This guide explains how to run the complete Voice RAG Prototype, test every layer, configure real providers, and identify the manual changes still needed for a production deployment.

## 1. What the Application Does

The current prototype flow is:

```text
Upload audio
  -> FFprobe metadata extraction
  -> FFmpeg normalization to mono 16 kHz WAV
  -> ASR transcription
  -> original transcript persistence
  -> English translation
  -> PII redaction
  -> redacted transcript persistence
  -> sentence-aware chunking
  -> BGE-M3/mock embeddings
  -> PostgreSQL/pgvector storage
  -> vector search + keyword search
  -> Reciprocal Rank Fusion
  -> cross-encoder/mock reranking
  -> frontend results
```

The backend owns all provider calls and secrets. The frontend only calls backend HTTP endpoints.

## 2. Repository Layout

Important directories and files:

```text
backend/
  app/
    api/v1/audio.py                 Upload, status, and result endpoints
    api/v1/search.py                Search endpoint
    config.py                       Environment-backed settings
    db/database.py                  SQLAlchemy engine and session
    db/models.py                    Audio, transcript, chunk, embedding models
    observability/tracing.py        Optional Langfuse tracing
    providers/asr/                  Sarvam and mock ASR providers
    providers/translation/          Gemini and mock translation providers
    providers/embedding/            BGE-M3 and mock embedding providers
    providers/reranking/            Cross-encoder and mock rerankers
    services/audio_service.py       Upload and FFmpeg processing
    services/processing_service.py  Complete synchronous pipeline
    services/pii_service.py         Presidio redaction
    services/transcript_chunking_service.py
    services/embedding_service.py
    services/retrieval_service.py
    services/rrf_service.py
    services/reranker_service.py
  tests/                            Backend tests
frontend/
  src/App.tsx                       Complete React workflow
  src/styles.css                    UI styling
  vite.config.ts                    Dev server and API proxy
  tsconfig.json                     TypeScript configuration
IMPLEMENTATION_WALKTHROUGH.md       Feature history
RUN_AND_TEST_GUIDE.md               This runbook
```

## 3. Prerequisites

### Required

- Windows 10 or 11.
- Docker Desktop with Docker Compose enabled.
- Git is recommended, although the current workspace may not contain Git metadata.
- At least 8 GB RAM for the backend dependencies. More memory is recommended if using Presidio, BGE-M3, or a cross-encoder locally.
- Internet access for Docker image/package/model downloads.

### Optional for host-based development

- Python 3.11.
- Node.js 20 or newer.
- npm.
- FFmpeg and FFprobe on the host if running the backend outside Docker.
- PostgreSQL 16 with pgvector if running the database outside Docker.

## 4. First-Time Setup with Docker

Open PowerShell at the repository root:

```powershell
Set-Location "C:\Users\bavag\Desktop\voice_processing\voice-rag-prototype"
```

Confirm the expected files exist:

```powershell
Get-ChildItem
Test-Path .env.example
Test-Path docker-compose.yml
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`. It can contain provider credentials.

## 5. Local Provider Modes

Docker Compose defaults the backend to mock providers unless values are explicitly supplied through the shell or `.env`:

```text
ASR_PROVIDER=mock
TRANSLATION_PROVIDER=mock
EMBEDDING_PROVIDER=mock
RERANKER_PROVIDER=mock
```

This is the recommended first run. It avoids external API calls, API keys, and large embedding/reranker model downloads.

To use real providers, set these values in `.env` before starting the backend:

```text
ASR_PROVIDER=sarvam
SARVAM_API_KEY=your_real_sarvam_key

TRANSLATION_PROVIDER=gemini
GEMINI_API_KEY=your_real_gemini_key

EMBEDDING_PROVIDER=bge-m3
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

RERANKER_PROVIDER=cross-encoder
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

The BGE-M3 and cross-encoder models are downloaded by `sentence-transformers` when first used. This may take time and disk space.

## 6. Start the Full Application

Build and start all services:

```powershell
docker compose up -d --build
```

The services are:

| Service | URL/Port | Purpose |
|---|---:|---|
| Frontend | `http://localhost:5173` | React/Vite UI |
| Backend | `http://localhost:8000` | FastAPI API |
| Database | `localhost:5432` | PostgreSQL + pgvector |

Check service status:

```powershell
docker compose ps
```

Follow backend logs:

```powershell
docker compose logs -f backend
```

Stop viewing logs with `Ctrl+C`; that does not stop the containers.

Stop the application:

```powershell
docker compose down
```

Stop the application and delete the PostgreSQL volume. This permanently deletes the local database:

```powershell
docker compose down -v
```

## 7. Verify the Database

Check PostgreSQL health:

```powershell
docker compose exec db pg_isready -U postgres -d voicedb
```

Open a PostgreSQL shell:

```powershell
docker compose exec db psql -U postgres -d voicedb
```

Inside `psql`, enable pgvector if necessary and inspect tables:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
\dt
\d audio_documents
\d transcripts
\d chunks
\d chunk_embeddings
\q
```

The application currently creates tables through SQLAlchemy `Base.metadata.create_all()` during backend import. There is no migration system yet.

## 8. Verify the Backend API

Check health from PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "database": "healthy"
}
```

Open the interactive API documentation:

```text
http://localhost:8000/docs
```

Alternative OpenAPI JSON endpoint:

```text
http://localhost:8000/openapi.json
```

## 9. Test Upload Through the API

Use an audio file that exists on your machine. Replace the path below:

```powershell
$audioPath = "C:\path\to\sample.mp3"
```

Upload with optional metadata:

```powershell
$form = @{
  file = Get-Item $audioPath
  language = "kn-IN"
  region = "Karnataka"
  speaker_id = "speaker-01"
}
$upload = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/audio/upload" -Method Post -Form $form
$upload | ConvertTo-Json -Depth 8
```

The synchronous prototype runs processing during this request. A successful response should have:

```text
processing_status = completed
processing_stage  = completed
```

If processing fails, the response records:

```text
processing_status = failed
processing_stage  = failed
processing_error  = failure description
```

Save the uploaded audio ID:

```powershell
$audioId = $upload.id
```

Get the audio record:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/audio/$audioId" | ConvertTo-Json -Depth 8
```

Get processing status:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/audio/$audioId/status" | ConvertTo-Json -Depth 8
```

Get transcript variants and child chunks:

```powershell
$result = Invoke-RestMethod "http://localhost:8000/api/v1/audio/$audioId/result"
$result | ConvertTo-Json -Depth 12
```

The result should contain:

- Original transcript.
- English translation.
- Redacted English transcript.
- Ordered child chunks.
- Chunk timestamps.
- Audio and chunk metadata.

## 10. Test Search Through the API

Search all regions:

```powershell
$body = @{
  query = "What was discussed in the meeting?"
  top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/search" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 12
```

Search one region:

```powershell
$body = @{
  query = "meeting discussion"
  region = "Karnataka"
  top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/search" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 12
```

The response contains four independent views of the pipeline:

```text
vector_results      Dense pgvector results
keyword_results     PostgreSQL full-text results
rrf_results         Reciprocal Rank Fusion candidates, up to 20
reranked_results    Final cross-encoder/mock results, up to top_k
```

Each result includes:

```text
chunk_id
content
score
rank
metadata
```

## 11. Test Through the Frontend

Open:

```text
http://localhost:5173
```

### Upload Audio

1. Select an audio file.
2. Select a region if known.
3. Enter a speaker ID if available.
4. Select `Process audio`.
5. Wait for the processing request to finish.

### Processing Status

The processing view displays:

- Audio preprocessing.
- ASR.
- Translation.
- PII redaction.
- Chunking.
- Embedding.
- Indexing.

The current backend workflow is synchronous. The progress display is a prototype stage presentation while the upload request runs; a future queue/worker should provide real-time persisted progress.

### Transcript Result

Verify that the result view shows:

- Original transcript.
- English translation.
- PII-redacted English.
- Region, speaker, duration, and language metadata.
- Child chunks.
- Start and end timestamps.
- Provider/model details where available.

### Search

1. Open the Search view.
2. Enter a natural-language query.
3. Optionally select a region.
4. Set `Top` between 1 and 20.
5. Submit the search.
6. Review final reranked results and all intermediate result groups.

## 12. Run Frontend Locally Without Docker

Install dependencies:

```powershell
Set-Location "frontend"
npm install
```

Build for production:

```powershell
npm run build
```

Start Vite:

```powershell
npm run dev
```

Open `http://localhost:5173`.

The Vite config proxies `/api` to `http://backend:8000`, which works inside the Docker Compose network. When running Vite directly on the host, change the proxy target manually to `http://localhost:8000` if the hostname `backend` cannot resolve:

```typescript
proxy: {
  '/api': 'http://localhost:8000'
}
```

The backend CORS configuration currently allows `http://localhost:5173`.

## 13. Run Backend Locally Without Docker

Create and activate a virtual environment:

```powershell
Set-Location "backend"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The requirements use `pydantic==2.7.4`, which satisfies `sarvamai==0.1.0` while preserving the Pydantic 2 APIs used by the application. The Sarvam pin remains unchanged. The Google stack is also constrained with `google-api-core==2.11.1`, `googleapis-common-protos==1.56.4`, and `protobuf==4.25.3` for compatibility with `google-generativeai==0.3.2`. Langfuse is pinned to `2.0.1` to avoid newer OpenTelemetry protobuf requirements.

Set a host database URL:

```powershell
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/voicedb"
$env:ASR_PROVIDER = "mock"
$env:TRANSLATION_PROVIDER = "mock"
$env:EMBEDDING_PROVIDER = "mock"
$env:RERANKER_PROVIDER = "mock"
```

Start FastAPI:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Keep the terminal running. Start the frontend in a second terminal.

## 14. Run Tests

### Focused chunking tests

From the repository root in a dependency-ready backend environment:

```powershell
pytest backend/tests/test_transcript_chunking.py -q
```

### Focused embedding tests

```powershell
pytest backend/tests/test_embeddings.py -q
```

### Focused retrieval/fusion tests

```powershell
pytest backend/tests/test_retrieval.py -q
```

### Mocked end-to-end pipeline test

```powershell
pytest backend/tests/test_end_to_end_pipeline.py -q
```

### Complete backend suite

```powershell
pytest backend/tests -q
```

When using Docker with the current stale image, install missing lightweight packages in the temporary container before running tests:

```powershell
docker compose run --rm backend sh -c "pip install python-multipart==0.0.6 pgvector==0.2.5; pytest tests -q"
```

For a clean dependency image, rebuild after dependency resolution:

```powershell
docker compose build backend
```

Pip dry-run resolution succeeds with the current requirements. A full image build may take significant time and disk space because `sentence-transformers` pulls a large Torch/CUDA runtime.

### Frontend build test

```powershell
Set-Location frontend
npm install
npm run build
```

### Editor diagnostics

In VS Code, open the Problems panel after files load. The relevant backend and frontend files should report no syntax/type diagnostics when the configured interpreters and dependencies are available.

## 15. Manual Changes Still Required

These are not required for the mock prototype demo, but should be addressed before production use.

### Dependency resolution

Resolve the current `pydantic` and `sarvamai` version conflict in `backend/requirements.txt`. Then rebuild the backend image instead of installing packages ad hoc in each test container.

Also ensure the built image includes every declared runtime dependency, including:

- `python-multipart`.
- `pgvector`.
- `sentence-transformers`.
- `langfuse`.
- Gemini and Sarvam SDKs when real providers are enabled.

### Database migrations

Add Alembic migrations for:

- `audio_documents` processing fields.
- `transcripts`.
- `chunks`.
- `chunk_embeddings`.
- pgvector extension creation.
- PostgreSQL full-text indexes.
- Vector indexes such as HNSW or IVFFlat after deciding the distance metric.

Do not depend on import-time `create_all()` for production schema changes.

### Database startup

Move database initialization out of module import. Add a startup health/retry strategy and fail clearly when PostgreSQL is unavailable.

### Real-time processing status

Replace synchronous processing with a background worker or task queue. Store stage transitions as durable records and have the frontend poll or subscribe to status updates.

### Provider credentials

Provide production secrets through a secret manager or protected deployment environment. Never put Sarvam, Gemini, Langfuse secret keys, or model credentials in React or committed files.

### Audio security

Add:

- Maximum upload size.
- MIME/content validation, not only filename extension validation.
- Authentication and authorization.
- Rate limiting.
- Malware scanning if required by deployment policy.
- Cleanup for failed uploads and failed FFmpeg jobs.
- Protected download URLs instead of exposing filesystem paths.

### Observability

Set Langfuse variables on the backend only:

```text
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Verify traces for all stages in the Langfuse dashboard. Add request IDs, structured logs, latency, provider errors, and token/cost metrics.

### Search quality

Add PostgreSQL indexes and evaluate:

- BGE-M3 embedding dimension and normalization.
- Cross-encoder model choice.
- RRF `k` value.
- Candidate count before reranking.
- Region filter behavior.
- Empty/no-result behavior.
- Duplicate and overlapping chunks.

RRF and reranking are currently evaluative outputs only; no answer-generation/RAG layer exists yet.

## 16. Troubleshooting

### `Form data requires python-multipart`

The image is stale or dependencies were not rebuilt. Run:

```powershell
docker compose build backend
```

If the build is blocked by dependency resolution, use the temporary install command from the test section while fixing `requirements.txt`.

### `Could not resolve host backend` from host Vite

The Docker service hostname is only available inside the Compose network. Change the Vite proxy target to `http://localhost:8000` when running Vite on the host.

### `CORS` browser errors

Confirm the frontend is using `http://localhost:5173` and the backend is running on port `8000`. The current backend allows the local frontend origin only.

### `SARVAM_API_KEY must be provided`

Set `ASR_PROVIDER=mock` for local testing or supply a valid backend-only `SARVAM_API_KEY`.

### `GEMINI_API_KEY must be provided`

Set `TRANSLATION_PROVIDER=mock` for local testing or supply a valid backend-only `GEMINI_API_KEY`.

### BGE-M3 or CrossEncoder download failures

Use mock providers first. For real providers, check internet access, disk space, Hugging Face access, and container memory.

### PostgreSQL vector errors

Check that the database is the pgvector image and that the extension is enabled:

```powershell
docker compose exec db psql -U postgres -d voicedb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### SQLite `readonly database` test errors

The existing test fixture uses a file-backed SQLite database named `test.db` inside the backend test working directory. Close processes holding the file, remove stale test artifacts, or change the fixture to use a unique temporary/in-memory database. PostgreSQL-specific vector and full-text behavior still requires PostgreSQL integration tests.

### Gemini test reports `genai` is `None`

The test container does not have the Gemini SDK installed. Rebuild the image after dependency resolution or install the declared package in the test environment.

## 17. Current Known Boundaries

- The frontend is functional but intentionally compact and prototype-oriented.
- Processing is synchronous, so the Processing screen does not yet receive live server-side progress updates.
- Mock providers are deterministic and do not represent production model quality.
- Search requires persisted child chunks and embeddings.
- PostgreSQL full-text and pgvector queries are not fully exercised by the SQLite unit fixture.
- RAG answer generation is not implemented.
- There is no authentication or multi-user isolation.

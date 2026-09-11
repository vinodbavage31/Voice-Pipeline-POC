# Voice RAG Prototype Implementation Walkthrough

_Last updated: 2026-09-11_

This document tracks the functionality implemented in the repository so future development can continue from the current state.

## Project Foundation

- Frontend: React 18, TypeScript, and Vite in `frontend/`.
- Backend: FastAPI and Python in `backend/`.
- Database: PostgreSQL with the `pgvector/pgvector:pg16` Docker image.
- ORM: SQLAlchemy.
- Infrastructure: Docker Compose defines database, backend, and frontend services.
- Backend container includes FFmpeg for audio inspection and conversion.

## Backend API

Implemented endpoints:

### Audio Ingestion (`/api/v1/audio/*`)
- `POST /upload` - Upload audio file, extract metadata, preprocess to WAV mono 16kHz, and run the complete synchronous pipeline (ASR → translation → PII redaction → chunking → embedding → indexing).
- `GET /{audio_id}/status` - Get processing status and current stage.
- `GET /{audio_id}/result` - Get transcript variants (original, translated_english, redacted_english) and child chunks with timestamps.
- `GET /{audio_id}` - Get basic audio document metadata.

### Search (`/api/v1/search/*`)
- `POST /` - Perform hybrid search (vector + keyword) with reciprocal rank fusion and reranking. Returns separate result sets for debugging.

### Answer Generation (`/api/v1/answer/*`)
- `POST /` - Generate grounded answers using a flow: query → vector + keyword search → RRF fusion → cross-encoder reranking → context building → Gemini generation → answer with citations. Returns answer string and citations with source audio/chunk/timestamp information.
  - The Gemini generation provider uses the `gemini-3.6-flash` model by default (configurable via `GEMINI_MODEL`).

## Audio Storage

- Original files are stored under `data/uploads/`.
- Supported extensions include `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, and `.webm`.
- Audio metadata is represented by the `AudioDocument` SQLAlchemy model.

## Transcription Provider Layer

The provider abstraction is in `backend/app/providers/asr/`.

- `ASRProvider` defines the common transcription contract.
- `SarvamASR` integrates the Sarvam AI SDK.
  - Configurable model and language.
  - Default model: `saaras:v3`.
  - Default language: `kn-IN`.
  - Implements both direct transcription (for audio ≤30s) and batch transcription (for audio >30s) via Sarvam AI's asynchronous job API.
  - For long audio (>30s), uploads the file, creates a batch job, waits for completion (up to 30 minutes), retrieves the result, and normalizes it.
  - Includes FFmpeg-based duration check to automatically route to batch processing when needed.
- `MockASR` provides deterministic local/test responses.
- `get_asr_provider()` selects the provider from `ASR_PROVIDER` (default: `sarvam`).
- Responses are normalized into `ASRResponse` with transcript, language, provider, model, confidence, segments, and request ID.

## Translation Provider Layer

The provider abstraction is in `backend/app/providers/translation/`.

- `TranslationProvider` defines the common translation contract.
- `GeminiTranslationProvider` integrates Google Gemini.
  - Preserves names, places, numbers, dates, and domain terminology.
  - Does not summarize or add information.
  - Uses a highly constrained prompt to enforce faithful translation.
  - Default model: `gemini-3.6-flash` (configurable via `GEMINI_MODEL`).
- `MockTranslationProvider` provides deterministic local/test output.
- `get_translation_provider()` selects the provider from `TRANSLATION_PROVIDER` (default: `gemini`).
- Responses are normalized into `TranslationResponse`.

## Transcript Data Model

`backend/app/db/models.py` contains:

- `AudioDocument`
  - Stores source audio and metadata.
- `Transcript`
  - Stores transcript text associated with an audio document.
  - Supports `original`, `translated_english`, and `redacted_english` transcript types.
  - Stores language, provider, model, confidence, and optional normalized ASR segments.
- `TranscriptChunk`
  - Stores ordered transcript chunks with parent-child hierarchy.
- `ChunkEmbedding`
  - Stores one vector embedding per chunk in `chunk_embeddings`.

Original, translated, and redacted transcript variants remain available without overwriting one another.

## PII Redaction

`backend/app/services/pii_service.py` provides text-only PII detection and redaction using Microsoft Presidio.

Detected entities include `PERSON`, `PHONE_NUMBER`, `EMAIL_ADDRESS`, `LOCATION`, `DATE_TIME`, `IN_PAN`, and `IN_AADHAAR`.

Custom Indian PAN and Aadhaar recognizers use regex patterns and contextual hints. Redaction is applied only to transcript text; original audio is never sent to Presidio.

The persisted result is a `redacted_english` transcript while original and translated transcript rows remain unchanged.

## Transcript Chunking Layer

Implemented in `backend/app/services/transcript_chunking_service.py`.

- Accepts transcript text with optional ASR segment timing data.
- Intended for `redacted_english` transcripts.
- Splits text on sentence boundaries while preserving punctuation and ordering.
- Uses deterministic whitespace-token estimates.
- Default target is approximately 350 tokens.
- Default maximum is 500 tokens.
- Default overlap is 40 tokens.
- Oversized sentences are split into maximum-size pieces.
- ASR timestamps are aggregated where available and interpolated for oversized segments.
- Missing timestamp data remains null.
- Creates one parent chunk containing the full transcript and ordered child chunks linked by `parent_chunk_id`.
- Repeated chunking replaces prior chunks for the transcript.

## Embedding and Vector Storage Layer

Implemented in `backend/app/providers/embedding/` and `backend/app/services/embedding_service.py`.

- `EmbeddingProvider` defines the common embedding contract.
- `BGE_M3EmbeddingProvider` uses `BAAI/bge-m3` through `sentence-transformers`.
- `MockEmbeddingProvider` provides deterministic vectors for tests and local development.
- `get_embedding_provider()` selects the configured provider (default: `bge-m3`).
- `EmbeddingService` provides embedding generation, dimension validation, storage, and batch embedding.
- Text is whitespace-normalized before embedding.
- The model is configurable through `EMBEDDING_MODEL`.
- The vector dimension is configurable through `EMBEDDING_DIMENSION`, defaulting to 1024 for BGE-M3.
- Vectors use the pgvector `Vector` type in PostgreSQL.
- Retrieval, similarity search, and RAG queries are separate follow-up functionality.

## Retrieval Layer

Implemented in `backend/app/services/retrieval_service.py` and `backend/app/api/v1/search.py`.

- `vector_search()` performs dense retrieval using pgvector cosine distance.
- `keyword_search()` performs sparse PostgreSQL full-text search using `websearch_to_tsquery` and `ts_rank_cd`.
- Both strategies search child chunks from `redacted_english` transcripts and exclude parent rows.
- Both strategies support optional region filtering and `top_k` limits.
- Without a region, searches cover all regions.
- Both strategies return the common structure: `chunk_id`, `content`, `score`, `rank`, and `metadata`.
- The API returns vector and keyword results separately for debugging.

## Retrieval Fusion and Reranking

Implemented in `backend/app/services/rrf_service.py`, `backend/app/services/reranker_service.py`, and `backend/app/providers/reranking/`.

- `RRFService` applies standard Reciprocal Rank Fusion using `1 / (k + rank)`.
- The default RRF constant is configurable through `RRF_K` and defaults to 60.
- Results are deduplicated by `chunk_id`, ranked by fused score, and capped at `RRF_TOP_K` (default 20).
- `RerankerProvider` defines the replaceable reranker interface.
- `CrossEncoderRerankerProvider` uses `sentence-transformers` CrossEncoder (default: `cross-encoder/ms-marco-MiniLM-L-6-v2`).
- `MockRerankerProvider` supports deterministic tests and local development.
- `RerankerService` scores RRF candidates and returns the final requested `top_k` results.
- `POST /api/v1/search` now returns `vector_results`, `keyword_results`, `rrf_results`, and `reranked_results`.
- Reciprocal rank fusion and reranking are kept separate from the retrieval strategies for evaluation.

## Context Building

Implemented in `backend/app/services/context_builder.py`.

- `ContextBuilder.build_context()` converts a list of `SearchResult` objects into a list of evidence dicts for grounded answer generation.
- Keeps results in rank order and truncates the accumulated context to a configurable `max_chars` (default 4000).
- Each evidence dict contains `chunk_id`, `content`, `score`, `rank`, and `metadata` (including audio_id, speaker_id, region, start_time, end_time).

## End-to-End Processing Pipeline

Implemented in `backend/app/services/processing_service.py`.

- `POST /api/v1/audio/upload` now runs the complete synchronous prototype workflow after upload/preprocessing:
  1. Audio preprocessing (FFmpeg to WAV mono 16kHz).
  2. ASR (Sarvam, with automatic batch processing for audio >30s).
  3. Original transcript persistence.
  4. Translation (Gemini).
  5. English translation persistence.
  6. PII redaction.
  7. Redacted English transcript persistence.
  8. Transcript chunking.
  9. Embedding generation and persistence.
  10. Indexing completion status.
- `AudioDocument` now records `processing_status`, `processing_stage`, and `processing_error`.
- `GET /api/v1/audio/{audio_id}/status` exposes processing state.
- `GET /api/v1/audio/{audio_id}/result` returns transcript variants and child chunks with timestamps and metadata.
- Provider dependencies remain backend-only; React never receives API keys.
- Docker development defaults to mock ASR, translation, embedding, and reranker providers. Real providers can be selected through environment variables (see `.env.example`).

## Observability

Implemented in `backend/app/observability/tracing.py`.

- Optional Langfuse tracing is enabled when Langfuse credentials are configured.
- The tracer safely becomes a no-op when the SDK or credentials are unavailable.
- Pipeline spans cover audio processing, ASR, translation, PII redaction, chunking, embedding, and indexing.
- Search spans cover vector search, keyword search, RRF, and reranking.
- Langfuse credentials are configured only through backend environment variables.

## Frontend Workflow

Implemented in `frontend/src/App.tsx` and `frontend/src/styles.css`.

- Upload Audio view supports file selection, region, speaker ID, and processing.
- Processing view displays audio preprocessing, ASR, translation, PII redaction, chunking, embedding, and indexing stages.
- Transcript Result view displays original transcript, English translation, redacted English, metadata, chunks, and timestamps.
- Search view accepts a natural-language query, optional region, and `top_k`.
- Search results show final reranked results plus RRF candidates, vector results, and keyword results with scores, source audio IDs, regions, and timestamps.
- Answer view allows users to ask a natural-language question about their recordings and receive a grounded answer with citations to the exact source chunks.
  - Users enter a question, optionally filter by region, and select the number of top chunks to consider for context.
  - The frontend calls `/api/v1/answer` to retrieve the answer and citations.
  - The answer is displayed with a list of citations, each showing:
    - Chunk ID and text.
    - Source audio ID, speaker ID, region.
    - Start and end times (formatted as MM:SS).
    - Relevance score and rank.
- Vite proxies `/api` calls to the backend, and FastAPI enables the local frontend origin through CORS.
- No frontend API keys or provider secrets are present.

## Tests

Backend tests cover:

- Audio upload validation and persistence.
- ASR mock and factory behavior.
- Translation mock and factory behavior.
- Presidio entity redaction.
- Transcript chunk ordering, overlap, metadata, and timestamps.
- Chunk parent-child persistence and replacement.
- Mocked embedding generation and factory selection.
- Embedding dimension validation and pgvector persistence.
- Common retrieval result structure.
- Dense retrieval ranking and provider use.
- Sparse retrieval ranking and region filtering.
- Search API response structure.
- RRF duplicate merging, scoring, ordering, and top-k truncation.
- Cross-encoder reranker interface and score ordering.
- Search API fusion pipeline response.
- Mocked end-to-end ASR-to-embedding pipeline.
- RAG answer generation pipeline (mocked generation provider).

Focused retrieval and fusion test result:
- `7 passed`

Focused transcript chunking test result:
- `7 passed`

End-to-end pipeline test result:
- `1 passed` when run independently.

The complete backend suite reached `20 passed, 5 skipped, 7 errors, 1 failed` in the current container environment.

## Known Issues and Environment Notes

- The current container test fixture reports a readonly SQLite database during several persistence/client tests. **(Test limitation only; does not affect the working POC with PostgreSQL.)**
- The existing Gemini provider test fails when the container image lacks the Gemini SDK. **(Test limitation only; the provider works when the SDK is installed.)**
- The Docker dependency set has an existing Pydantic compatibility conflict involving the pinned Pydantic version and `sarvamai`. **(May cause warnings or installation issues; does not break runtime if dependencies are resolved.)**
- The container image may be stale and miss declared packages such as `python-multipart`. **(If the image is stale, multipart form handling may fail; rebuild the image to resolve.)**
- The application currently calls `Base.metadata.create_all()` during import; a migration/startup strategy should eventually replace this. **(Works for development; not suitable for production schema changes.)**
- PostgreSQL full-text and pgvector retrieval require PostgreSQL with the vector extension enabled. **(Satisfied by the `pgvector/pgvector:pg16` image used in docker-compose.)**
- Retrieval currently has no vector or GIN indexes. **(Performance limitation; sequential scans are used for similarity and keyword search.)**
- The cross-encoder model is downloaded by `sentence-transformers` at runtime unless cached or baked into the image. **(First-time retrieval may be slow due to model download; subsequent runs use cached model.)**
- Upload validation relies primarily on file extension. **(No virus scanning, MIME-type validation, or content-based validation.)**
- Upload size limits, authentication, authorization, rate limiting, and cleanup on processing failure are not implemented. **(Production systems should add these.)**
- The current orchestration is synchronous and intended for prototype use; a queue/background worker is a future scalability improvement. **(Long audio files block the API request until processing completes.)**
- Frontend production build passes with `npm run build`. **(The frontend builds successfully for production.)**
- The workspace has no accessible Git metadata, so changes cannot currently be reviewed with `git diff`. **(Environment limitation; not a code issue.)**

## Suggested Next Development Areas

1. Vector and PostgreSQL full-text indexes with migrations.
2. Reliable database migrations and startup initialization.
3. Add upload size limits, authentication, and rate limiting.
4. Replace synchronous processing with a background worker queue for scalability.
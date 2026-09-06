# Voice RAG Prototype

## Prerequisites
- Docker
- Docker Compose
This is a proof-of-concept for a Voice RAG (Retrieval-Augmented Generation) application, currently featuring audio uploading, FFmpeg processing, ASR/translation pipeline, chunking, and PostgreSQL/pgvector storage.

## Quickstart
1. `copy .env.example .env`
2. `docker-compose up -d --build`
3. Frontend: http://localhost:5173
4. Backend API: http://localhost:8000
## Setup Instructions

### Windows

1. Install [Git](https://git-scm.com/downloads).
2. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
3. Clone the repository and navigate into it:
   ```cmd
   git clone <repository-url>
   cd voice-rag-prototype
   ```
4. Create your local `.env` file from the example template:
   ```cmd
   copy .env.example .env
   ```
5. Open `.env` and add any required environment values (or leave as defaults for mock providers).
6. Build and start the services:
   ```cmd
   docker compose up -d --build
   ```
7. Verify the services are running:
   - Frontend UI: [http://localhost:5173/](http://localhost:5173/)
   - Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Backend Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Linux

1. Install [Git](https://git-scm.com/downloads).
2. Install [Docker Engine](https://docs.docker.com/engine/install/).
3. Install the [Docker Compose plugin](https://docs.docker.com/compose/install/linux/).
4. Clone the repository and navigate into it:
   ```bash
   git clone <repository-url>
   cd voice-rag-prototype
   ```
5. Create your local `.env` file from the example template:
   ```bash
   cp .env.example .env
   ```
6. Open `.env` and add any required environment values (or leave as defaults for mock providers).
7. Build and start the services:
   ```bash
   docker compose up -d --build
   ```
8. Verify the services are running:
   - Frontend UI: [http://localhost:5173/](http://localhost:5173/)
   - Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Backend Health Check: [http://localhost:8000/health](http://localhost:8000/health)

## Managing the Application

View running containers:
```bash
docker compose ps
```

View backend logs:
```bash
docker compose logs --tail=100 backend
```

Stop the application:
```bash
docker compose down
```

**Note on Database Resetting:**
If you want to intentionally reset the database (wiping all tables and data), run:
```bash
docker compose down -v
```
The `-v` flag deletes the attached PostgreSQL volume. The pgvector extension and schema will be automatically re-initialized upon the next `docker compose up`.

## Detailed Run and Test Guide

See [RUN_AND_TEST_GUIDE.md](RUN_AND_TEST_GUIDE.md) for complete setup, frontend/backend commands, API and UI verification, testing, troubleshooting, provider configuration, and manual production changes.

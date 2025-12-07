# Guide Generator - Document to HTML Pipeline

A full-stack application that converts documents (PDFs, Word docs, etc.) into clean, organized HTML guides using Trelent's Data Ingestion API and OpenAI.

## What I Built

A complete document-to-HTML conversion pipeline with:

- **Next.js Web UI** - Drag-and-drop interface for non-technical users
- **Python Backend** - FastAPI server orchestrating a 5-stage processing pipeline
- **Real-time Progress** - Percentage-based tracking with polling updates
- **Topic Grouping** - AI-powered organization of documents by topic
- **Error Recovery** - Continue on failures + retry failed files
- **Duplicate Detection** - Prevents re-processing of already uploaded files
- **Rate Limiting** - 10 uploads/minute to prevent API overload
- **Concurrent Processing** - Multiple batches can run in parallel

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Trelent API token
- OpenAI API key

### Option 1: Docker Compose (Recommended)

```bash
# 1. Create .env file with your API keys
cp .env.example .env
# Edit .env with your TRELENT_API_TOKEN and OPENAI_API_KEY

# 2. Start everything
docker-compose up --build

# 3. Open http://localhost:3000
```

### Option 2: Manual Setup

**Backend (Python):**

```bash
cd scripts

# Install uv (if needed)
pip install uv

# Install dependencies
uv pip install -e .

# Create .env file
cp .env.example .env
# Edit with your API keys

# Run the server
python -m src.main
```

**Frontend (Next.js):**

```bash
cd web

# Install dependencies
npm install

# Run development server
npm run dev
```

Open http://localhost:3000 (frontend) and http://localhost:8000/docs (API docs)

## How It Works

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js UI    │────▶│  Python API     │────▶│  Trelent API    │
│  (Port 3000)    │     │  (Port 8000)    │     │  + OpenAI       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    SQLite DB    │
                        │  + File Store   │
                        └─────────────────┘
```

### 5-Stage Pipeline

| Stage | Progress | Description |
|-------|----------|-------------|
| 1. Upload | 0-5% | Validate and store uploaded files |
| 2. Ingest | 5-38% | Convert files to Markdown via Trelent API |
| 3. Group | 38-45% | AI analyzes content and groups by topic |
| 4. Rewrite | 45-85% | OpenAI rewrites and formats each group |
| 5. Output | 85-100% | Generate final HTML guides |

### Key Files

```
/scripts
├── src/
│   ├── api/           # FastAPI server and routes
│   ├── clients/       # Trelent + OpenAI API clients
│   ├── pipeline/      # 5-stage orchestrator
│   └── storage/       # SQLite + file management
└── pyproject.toml

/web
├── src/
│   ├── app/           # Next.js pages
│   ├── components/    # UI components
│   ├── hooks/         # Polling + upload hooks
│   └── lib/           # API client + types
└── package.json
```

## Key Tradeoffs

| Decision | Why | Alternative for Production |
|----------|-----|---------------------------|
| SQLite | Simple, no external deps | PostgreSQL with connection pooling |
| Polling (2s) | Works everywhere, simple | WebSockets for true real-time |
| Local file storage | Easy debugging | S3 or cloud storage |
| Sequential processing | Simpler error handling | Celery/RQ for parallelism |
| Single OpenAI model | Consistent results | Model routing by task type |

## What I'd Do Next

**With More Time:**

1. **Parallel Processing** - Use Celery or asyncio.gather for concurrent file ingestion
2. **WebSocket Updates** - Replace polling with real-time push notifications
3. **Template Customization** - Let users choose/edit HTML templates
4. **Search** - Add full-text search across generated guides
5. **Auth** - User accounts and per-user guide libraries
6. **Caching** - Cache Trelent/OpenAI responses for identical content
7. **Better Error Messages** - More specific error handling with suggested fixes
8. **Tests** - Unit tests for pipeline stages, E2E tests for UI
9. **Rate Limiting** - Respect API rate limits with proper backoff
10. **Monitoring** - Add logging, metrics, and alerting

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload files and start processing |
| GET | `/api/batches` | List all batches |
| GET | `/api/batches/{id}` | Get batch progress |
| POST | `/api/batches/{id}/retry` | Retry failed files |
| GET | `/api/guides` | List completed guides |
| GET | `/api/guides/{id}/html` | Get guide HTML content |

## Environment Variables

```env
# Required
TRELENT_API_TOKEN=your-token
OPENAI_API_KEY=your-key

# Optional
TRELENT_API_URL=https://api.trelent.com
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

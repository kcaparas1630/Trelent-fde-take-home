# Guide Pipeline Backend

Python FastAPI backend for the document-to-HTML conversion pipeline.

## Structure

```
scripts/
├── src/
│   ├── api/          # FastAPI server and routes
│   ├── clients/      # Trelent and OpenAI API clients
│   ├── pipeline/     # 5-stage orchestration pipeline
│   ├── storage/      # SQLite database and file storage
│   └── utils/        # Configuration and utilities
├── pyproject.toml    # Dependencies managed by uv
└── Dockerfile        # Docker build configuration
```

## Local Development

```bash
# Install dependencies using uv
uv pip install -e .

# Create .env file
cp .env.example .env
# Add your TRELENT_API_TOKEN and OPENAI_API_KEY

# Run the server
python -m src.main
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## Docker

```bash
# Build and run with Docker Compose (from project root)
docker-compose up --build
```

## API Endpoints

- `POST /api/upload` - Upload files and start processing
- `GET /api/batches/{id}` - Get batch progress (0-100%)
- `GET /api/guides` - List completed guides
- `GET /api/guides/{id}/html` - Download guide HTML

See `/docs` for full API documentation.

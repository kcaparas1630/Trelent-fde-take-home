# Python API Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml README.md ./

# Install dependencies
RUN uv pip install --system -e .

# Copy source code
COPY src/ ./src/

# Create data directory
RUN mkdir -p /app/data/uploads /app/data/outputs

# Expose port
EXPOSE 8000

# Run the API server
CMD ["python", "-m", "src.main"]

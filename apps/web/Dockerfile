# Django development Dockerfile
# For local development only - production uses Ansible direct deployment
#
# Build context: repo root (for access to pyproject.toml/uv.lock)
# Usage: docker compose up

FROM python:3.13-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (including dev for runserver auto-reload)
RUN uv sync --frozen --no-install-project

# Copy application code
COPY apps ./apps

# Run Django dev server
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "python", "apps/web/manage.py", "runserver", "0.0.0.0:8000"]

FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY apps ./apps

# Run Django dev server
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "python", "apps/web/manage.py", "runserver", "0.0.0.0:8000"]

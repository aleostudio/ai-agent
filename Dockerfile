FROM python:3.12-slim

# Just to test connection to Ollama inside the container
# RUN apt-get update && apt-get install -y iputils-ping curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV APP_HOST="0.0.0.0"
ENV APP_PORT=9201
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application
COPY . .
RUN uv sync --frozen --no-dev

CMD ["sh", "-c", "uv run uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}"]
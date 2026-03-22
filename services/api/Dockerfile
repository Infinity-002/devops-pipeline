FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml ./
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY packages/common/README.md packages/common/README.md
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/api/README.md services/api/README.md
COPY services/worker/pyproject.toml services/worker/pyproject.toml
COPY packages/common/src packages/common/src
COPY services/api/src services/api/src

RUN uv sync --package api-service --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uv", "run", "--package", "api-service", "uvicorn", "api_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

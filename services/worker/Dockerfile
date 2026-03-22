FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml ./
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY packages/common/README.md packages/common/README.md
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/worker/pyproject.toml services/worker/pyproject.toml
COPY services/worker/README.md services/worker/README.md
COPY packages/common/src packages/common/src
COPY services/worker/src services/worker/src

RUN uv sync --package worker-service --no-dev

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uv", "run", "--package", "worker-service", "python", "-m", "worker_service.main"]

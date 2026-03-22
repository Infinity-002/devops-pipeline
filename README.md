# Event-Driven Task Processing System

This project demonstrates an event-driven task processing system built with:

- `FastAPI` for the API service
- `RQ + Redis` for asynchronous background processing
- `React + Vite + Bun` for the web interface
- `Docker Compose` for local development
- `Kubernetes + Helm` for container orchestration
- `GitHub Actions` for CI automation

## Architecture

1. The web app submits a task to the API.
2. The API validates the request, stores task metadata in Redis, and enqueues a background job.
3. The worker service consumes the job from Redis and processes it independently.
4. The worker updates task status and result in Redis.
5. The web app polls the API to show real-time task progress.

## Supported Demo Tasks

- `image_processing`
- `csv_analysis`

## Repository Layout

```text
.
├── charts/
├── infra/k8s/
├── packages/common/
├── services/api/
├── services/worker/
├── web/
├── docker-compose.yml
└── .github/workflows/
```

## Local Development

### Option 1: Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Web: `http://localhost:5173`
- Redis: `localhost:6379`

### Option 2: Run Services Individually

Python services use `uv`.

```bash
uv sync
uv run --package api-service uvicorn api_service.main:app --host 0.0.0.0 --port 8000 --reload
uv run --package worker-service python -m worker_service.main
```

Frontend uses `bun`.

```bash
cd web
bun install
bun run dev --host
```

You also need a Redis instance running locally:

```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

## API Endpoints

- `GET /health/live`
- `GET /health/ready`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`

Example task creation:

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "csv_analysis",
    "payload": {
      "filename": "sales.csv",
      "csv_text": "name,amount\nAsha,10\nRavi,20"
    }
  }'
```

## Kubernetes

Apply the raw manifests:

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/
```

Or deploy with Helm:

```bash
helm upgrade --install task-system ./charts/task-system -n task-system --create-namespace
```

## CI/CD

The project now uses separate GitHub Actions workflows for CI and CD:

- PRs run `.github/workflows/ci.yml`
- pushes to `main` run `.github/workflows/deploy.yml`

### CI

Pull requests validate the project by:

- installing Python dependencies with `uv`
- running `ruff`
- running `pytest`
- installing frontend dependencies with `bun`
- building the frontend
- linting the Helm chart
- building Docker images for the API, worker, and web services

### CD

Pushes to `main` perform the full delivery pipeline:

1. validate the backend, frontend, and Helm chart
2. build Docker images for API, worker, and web
3. push those images to `GHCR`
4. connect to the Kubernetes cluster
5. deploy the release with `helm upgrade --install`

### Required GitHub Secrets

To make the deployment workflow work, configure:

- `KUBE_CONFIG_DATA`
  - base64-encoded kubeconfig for the target cluster

### Required Cluster Setup

The deployment workflow expects the cluster to be able to pull GHCR images.
If your GHCR packages are private, create an image pull secret in the deployment namespace:

```bash
kubectl create namespace task-system --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret docker-registry ghcr-auth \
  --namespace task-system \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  --docker-email=YOUR_EMAIL
```

Then add a GitHub repository variable:

- `GHCR_PULL_SECRET_NAME=ghcr-auth`

If your images are public, leave `GHCR_PULL_SECRET_NAME` unset and the deploy workflow will not inject an image pull secret.

## Notes

- Redis is used for both queueing and task state storage to keep the demo simple.
- Images are passed as data URLs and processed into preview artifacts by the worker.
- CSV analysis returns lightweight structural summaries rather than storing files on disk.
- The current pipeline is local-first and does not auto-deploy to a cloud cluster.
- The structure is ready for future additions such as Postgres, Prometheus metrics, or cloud deployment.

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from rq import Queue, Retry
from task_system_common.logging import configure_logging
from task_system_common.schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskRecord,
    TaskResponse,
)
from task_system_common.settings import get_settings
from task_system_common.store import TaskStore

from api_service.dependencies import get_redis, get_task_queue

logger = logging.getLogger(__name__)
RedisDependency = Annotated[Redis, Depends(get_redis)]
QueueDependency = Annotated[Queue, Depends(get_task_queue)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="Task System API", version="0.1.0", lifespan=lifespan)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "Request completed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready(redis: RedisDependency) -> dict[str, str]:
    redis.ping()
    return {"status": "ready"}


@app.post("/api/v1/tasks", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def create_task(
    request: CreateTaskRequest,
    redis: RedisDependency,
    queue: QueueDependency,
) -> CreateTaskResponse:
    store = TaskStore(redis)
    task = TaskRecord(task_type=request.task_type, payload=request.payload)
    store.save(task)
    queue.enqueue(
        "task_system_common.tasks.process_task",
        task.id,
        task.task_type,
        task.payload,
        job_id=task.id,
        retry=Retry(max=3, interval=[5, 15, 30]),
        result_ttl=3600,
        failure_ttl=3600,
    )
    logger.info("Task enqueued", extra={"task_id": task.id})
    return CreateTaskResponse(task_id=task.id, status="queued")


@app.get("/api/v1/tasks", response_model=list[TaskResponse])
def list_tasks(redis: RedisDependency) -> list[TaskResponse]:
    store = TaskStore(redis)
    tasks = store.list(limit=20)
    return [TaskResponse.model_validate(task.model_dump()) for task in tasks]


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, redis: RedisDependency) -> TaskResponse:
    store = TaskStore(redis)
    try:
        task = store.get(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    return TaskResponse.model_validate(task.model_dump())

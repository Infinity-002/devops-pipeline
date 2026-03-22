from __future__ import annotations

import json
from datetime import UTC, datetime

from redis import Redis

from task_system_common.schemas import TaskRecord, TaskStatus

TASK_KEY_PREFIX = "task"
TASK_INDEX_KEY = "tasks:index"


class TaskStore:
    def __init__(self, redis: Redis):
        self.redis = redis

    def save(self, task: TaskRecord) -> TaskRecord:
        task.updated_at = datetime.now(UTC)
        self.redis.set(self._task_key(task.id), task.model_dump_json())
        self.redis.lpush(TASK_INDEX_KEY, task.id)
        self.redis.ltrim(TASK_INDEX_KEY, 0, 99)
        return task

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict | None = None,
        error: str | None = None,
    ) -> TaskRecord:
        task = self.get(task_id)
        task.status = status
        task.result = result
        task.error = error
        return self.save(task)

    def get(self, task_id: str) -> TaskRecord:
        raw = self.redis.get(self._task_key(task_id))
        if raw is None:
            raise KeyError(task_id)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return TaskRecord.model_validate(json.loads(raw))

    def list(self, limit: int = 20) -> list[TaskRecord]:
        task_ids = self.redis.lrange(TASK_INDEX_KEY, 0, max(limit - 1, 0))
        items: list[TaskRecord] = []
        seen: set[str] = set()
        for task_id in task_ids:
            if isinstance(task_id, bytes):
                task_id = task_id.decode("utf-8")
            if task_id in seen:
                continue
            seen.add(task_id)
            try:
                items.append(self.get(task_id))
            except KeyError:
                continue
        return items

    @staticmethod
    def _task_key(task_id: str) -> str:
        return f"{TASK_KEY_PREFIX}:{task_id}"


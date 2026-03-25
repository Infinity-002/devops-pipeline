from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        items = self.lists.get(key, [])
        self.lists[key] = items[start:] if end == -1 else items[start : end + 1]

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self.lists.get(key, [])
        return items[start:] if end == -1 else items[start : end + 1]

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        return None


class FakeQueue:
    def __init__(self):
        self.enqueued: list[dict[str, object]] = []

    def enqueue(self, func: str, *args: object, **kwargs: object) -> None:
        self.enqueued.append(
            {
                "func": func,
                "args": args,
                "kwargs": kwargs,
            }
        )


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def fake_queue() -> FakeQueue:
    return FakeQueue()


@pytest.fixture
def parsed_tasks(fake_redis: FakeRedis):
    def _parsed_tasks() -> list[dict[str, object]]:
        return [json.loads(item) for item in fake_redis.lrange("tasks:recent", 0, -1)]

    return _parsed_tasks


@pytest.fixture
def sample_image_data_url() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color="red").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

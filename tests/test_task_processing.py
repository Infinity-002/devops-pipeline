import base64
import io

from PIL import Image
from task_system_common.schemas import TaskRecord, TaskStatus, TaskType
from task_system_common.store import TaskStore
from task_system_common.tasks import process_task


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
        if end == -1:
            self.lists[key] = items[start:]
        else:
            self.lists[key] = items[start : end + 1]

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self.lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start : end + 1]


def test_store_round_trip(monkeypatch):
    fake_redis = FakeRedis()
    store = TaskStore(fake_redis)  # type: ignore[arg-type]

    task = TaskRecord(
        task_type=TaskType.CSV_ANALYSIS,
        payload={"filename": "inventory.csv", "csv_text": "item,quantity\nwidget,5\n"},
    )
    store.save(task)

    loaded = store.get(task.id)

    assert loaded.id == task.id
    assert loaded.status == TaskStatus.QUEUED


def test_process_task_updates_status(monkeypatch):
    fake_redis = FakeRedis()
    store = TaskStore(fake_redis)  # type: ignore[arg-type]
    task = TaskRecord(
        task_type=TaskType.CSV_ANALYSIS,
        payload={"filename": "sales.csv", "csv_text": "name,amount\nA,10\nB,20\nC,\n"},
    )
    store.save(task)

    monkeypatch.setattr(
        "task_system_common.tasks.get_redis_connection",
        lambda _settings: fake_redis,
    )

    result = process_task(task.id, task.task_type, task.payload)
    updated = store.get(task.id)

    assert result["row_count"] == 3
    assert result["column_count"] == 2
    assert result["numeric_summary"]["amount"]["average"] == 15.0
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result == result


def test_process_image_task(monkeypatch):
    fake_redis = FakeRedis()
    store = TaskStore(fake_redis)  # type: ignore[arg-type]

    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="red").save(buffer, format="PNG")
    image_data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")

    task = TaskRecord(
        task_type=TaskType.IMAGE_PROCESSING,
        payload={"filename": "sample.png", "image_data_url": image_data_url},
    )
    store.save(task)

    monkeypatch.setattr(
        "task_system_common.tasks.get_redis_connection",
        lambda _settings: fake_redis,
    )

    result = process_task(task.id, task.task_type, task.payload)
    updated = store.get(task.id)

    assert result["original"]["width"] == 32
    assert result["original"]["image_data_url"].startswith("data:image/png;base64,")
    assert result["transforms"] == ["thumbnail", "grayscale", "sepia"]
    assert len(result["outputs"]) == 3
    assert result["outputs"][0]["image_data_url"].startswith("data:image/png;base64,")
    assert updated.status == TaskStatus.COMPLETED

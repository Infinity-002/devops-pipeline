from __future__ import annotations

import base64
import io

from PIL import Image
from task_system_common.schemas import TaskRecord, TaskStatus, TaskType
from task_system_common.store import TaskStore
from task_system_common.tasks import process_task


def test_store_round_trip(fake_redis):
    store = TaskStore(fake_redis)  # type: ignore[arg-type]

    task = TaskRecord(
        task_type=TaskType.CSV_ANALYSIS,
        payload={"filename": "inventory.csv", "csv_text": "item,quantity\nwidget,5\n"},
    )
    store.save(task)

    loaded = store.get(task.id)

    assert loaded.id == task.id
    assert loaded.status == TaskStatus.QUEUED


def test_process_task_updates_status(monkeypatch, fake_redis):
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


def test_process_image_task(monkeypatch, fake_redis):
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
    assert [output["key"] for output in result["outputs"]] == ["thumbnail", "grayscale", "sepia"]
    assert updated.status == TaskStatus.COMPLETED


def test_process_image_task_marks_failure_for_invalid_payload(monkeypatch, fake_redis):
    store = TaskStore(fake_redis)  # type: ignore[arg-type]
    task = TaskRecord(
        task_type=TaskType.IMAGE_PROCESSING,
        payload={
            "filename": "broken.png",
            "image_data_url": "data:text/plain;base64,QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo=",
        },
    )
    store.save(task)

    monkeypatch.setattr(
        "task_system_common.tasks.get_redis_connection",
        lambda _settings: fake_redis,
    )

    try:
        process_task(task.id, task.task_type, task.payload)
    except Exception as exc:
        assert "image MIME type" in str(exc)
    else:
        raise AssertionError("process_task should fail for invalid image payloads")

    updated = store.get(task.id)
    assert updated.status == TaskStatus.FAILED
    assert updated.error is not None

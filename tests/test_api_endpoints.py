xfrom __future__ import annotations

from api_service.dependencies import get_redis, get_task_queue
from api_service.main import app
from fastapi.testclient import TestClient
from task_system_common.schemas import TaskRecord, TaskType
from task_system_common.store import TaskStore


def test_create_task_enqueues_job(fake_redis, fake_queue, sample_image_data_url):
    def override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_task_queue] = lambda: fake_queue

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/tasks",
            json={
                    "task_type": "image_processing",
                    "payload": {
                        "filename": "demo.png",
                        "image_data_url": sample_image_data_url,
                        "transforms": ["thumbnail", "blur"],
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert len(fake_queue.enqueued) == 1
    assert fake_queue.enqueued[0]["func"] == "task_system_common.tasks.process_task"
    assert fake_queue.enqueued[0]["args"][0] == body["task_id"]
    saved_task = TaskStore(fake_redis).get(body["task_id"])  # type: ignore[arg-type]
    assert saved_task.id == body["task_id"]


def test_list_and_get_task_return_saved_records(fake_redis):
    store = TaskStore(fake_redis)  # type: ignore[arg-type]
    task = TaskRecord(
        task_type=TaskType.CSV_ANALYSIS,
        payload={"filename": "sales.csv", "csv_text": "name,amount\nAsha,10"},
    )
    store.save(task)

    def override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_redis

    try:
        client = TestClient(app)
        list_response = client.get("/api/v1/tasks")
        get_response = client.get(f"/api/v1/tasks/{task.id}")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == task.id
    assert get_response.status_code == 200
    assert get_response.json()["id"] == task.id


def test_get_task_returns_404_for_missing_record(fake_redis):
    def override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_redis

    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks/missing-task")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

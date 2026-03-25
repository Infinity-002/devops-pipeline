from __future__ import annotations

import pytest
from pydantic import ValidationError

from task_system_common.schemas import CreateTaskRequest, ImagePayload, TaskType


def test_image_payload_requires_at_least_one_transform(sample_image_data_url):
    with pytest.raises(ValidationError) as exc_info:
        ImagePayload(
            filename="sample.png",
            image_data_url=sample_image_data_url,
            transforms=[],
        )

    assert "At least one image transform must be selected" in str(exc_info.value)


def test_image_payload_deduplicates_transform_values(sample_image_data_url):
    payload = ImagePayload(
        filename="sample.png",
        image_data_url=sample_image_data_url,
        transforms=["thumbnail", "thumbnail", "blur"],
    )

    assert payload.transforms == ["thumbnail", "blur"]


def test_create_task_request_rejects_empty_csv_rows():
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskRequest(
            task_type=TaskType.CSV_ANALYSIS,
            payload={"filename": "empty.csv", "csv_text": "\n   \n"},
        )

    assert "csv_text must contain at least one non-empty row" in str(exc_info.value)

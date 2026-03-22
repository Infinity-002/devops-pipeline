from __future__ import annotations

import base64
import csv
import io
import logging
from typing import Any

from PIL import Image, UnidentifiedImageError

from task_system_common.queue import get_redis_connection
from task_system_common.schemas import CsvPayload, ImagePayload, TaskStatus, TaskType
from task_system_common.settings import get_settings
from task_system_common.store import TaskStore

logger = logging.getLogger(__name__)


def process_task(task_id: str, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    redis = get_redis_connection(settings)
    store = TaskStore(redis)

    logger.info("Starting task", extra={"task_id": task_id})
    store.update_status(task_id, TaskStatus.RUNNING)

    try:
        if task_type == TaskType.IMAGE_PROCESSING:
            data = ImagePayload.model_validate(payload)
            result = _process_image(data)
        elif task_type == TaskType.CSV_ANALYSIS:
            data = CsvPayload.model_validate(payload)
            result = _analyze_csv(data)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")

        store.update_status(task_id, TaskStatus.COMPLETED, result=result, error=None)
        logger.info("Completed task", extra={"task_id": task_id})
        return result
    except Exception as exc:
        store.update_status(task_id, TaskStatus.FAILED, result=None, error=str(exc))
        logger.exception("Task failed", extra={"task_id": task_id})
        raise


def _process_image(payload: ImagePayload) -> dict[str, Any]:
    try:
        header, encoded = payload.image_data_url.split(",", maxsplit=1)
    except ValueError as exc:
        raise ValueError("image_data_url must be a valid data URL") from exc

    if not header.startswith("data:image/"):
        raise ValueError("image_data_url must contain an image MIME type")

    try:
        image_bytes = base64.b64decode(encoded)
    except ValueError as exc:
        raise ValueError("image_data_url contains invalid base64 data") from exc

    try:
        with Image.open(io.BytesIO(image_bytes)) as source_image:
            source_image.load()
            original_width, original_height = source_image.size
            source_format = source_image.format or "PNG"

            thumbnail = source_image.copy()
            thumbnail.thumbnail((320, 320))

            grayscale = source_image.convert("L").convert("RGB")
            grayscale.thumbnail((320, 320))

            return {
                "filename": payload.filename,
                "original": {
                    "format": source_format,
                    "width": original_width,
                    "height": original_height,
                },
                "thumbnail": {
                    "width": thumbnail.width,
                    "height": thumbnail.height,
                    "image_data_url": _image_to_data_url(thumbnail),
                },
                "grayscale_preview": {
                    "width": grayscale.width,
                    "height": grayscale.height,
                    "image_data_url": _image_to_data_url(grayscale),
                },
            }
    except UnidentifiedImageError as exc:
        raise ValueError("Uploaded file is not a supported image") from exc


def _analyze_csv(payload: CsvPayload) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(payload.csv_text))
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        raise ValueError("CSV file must include a header row")

    rows = list(reader)
    if not rows:
        raise ValueError("CSV file must include at least one data row")

    missing_values = {field: 0 for field in fieldnames}
    numeric_columns: dict[str, list[float]] = {field: [] for field in fieldnames}

    for row in rows:
        for field in fieldnames:
            raw_value = (row.get(field) or "").strip()
            if raw_value == "":
                missing_values[field] += 1
                continue
            try:
                numeric_columns[field].append(float(raw_value))
            except ValueError:
                continue

    numeric_summary = {}
    for field, values in numeric_columns.items():
        if not values:
            continue
        numeric_summary[field] = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "average": round(sum(values) / len(values), 2),
        }

    sample_rows = rows[:5]

    return {
        "filename": payload.filename,
        "row_count": len(rows),
        "column_count": len(fieldnames),
        "columns": fieldnames,
        "missing_values": missing_values,
        "numeric_summary": numeric_summary,
        "sample_rows": sample_rows,
    }


def _image_to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

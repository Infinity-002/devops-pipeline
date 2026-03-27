from __future__ import annotations

import base64
import csv
import io
import logging
import time
from typing import Any

from PIL import Image, ImageFilter, UnidentifiedImageError

from task_system_common.queue import get_redis_connection
from task_system_common.schemas import (
    CsvPayload,
    ImagePayload,
    ImageTransform,
    TaskStatus,
    TaskType,
)
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
        if settings.task_processing_delay_seconds > 0:
            logger.info(
                "Applying demo processing delay",
                extra={
                    "task_id": task_id,
                    "delay_seconds": settings.task_processing_delay_seconds,
                },
            )
            time.sleep(settings.task_processing_delay_seconds)

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
            normalized_image = source_image.convert("RGB")
            original_width, original_height = normalized_image.size
            source_format = source_image.format or "PNG"
            aspect_ratio = round(original_width / original_height, 3) if original_height else None

            outputs = []
            for transform in payload.transforms:
                image = _apply_transform(normalized_image, transform)
                outputs.append(
                    {
                        "key": transform.value,
                        "label": _transform_label(transform),
                        "description": _transform_description(transform),
                        "width": image.width,
                        "height": image.height,
                        "image_data_url": _image_to_data_url(image),
                    }
                )

            return {
                "filename": payload.filename,
                "original": {
                    "format": source_format,
                    "width": original_width,
                    "height": original_height,
                    "size_bytes": len(image_bytes),
                    "aspect_ratio": aspect_ratio,
                    "image_data_url": _image_to_data_url(_preview_image(normalized_image)),
                },
                "transforms": [transform.value for transform in payload.transforms],
                "outputs": outputs,
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

    grouped_chart = _build_grouped_species_chart(rows, fieldnames, numeric_summary)
    chart_columns = [
        {"column": field, "value": numeric_summary[field]["average"]}
        for field in fieldnames
        if field in numeric_summary
    ][:3]
    fallback_chart = {
        "kind": "columns",
        "metric": "average",
        "columns": chart_columns,
    }

    return {
        "filename": payload.filename,
        "row_count": len(rows),
        "column_count": len(fieldnames),
        "columns": fieldnames,
        "missing_values": missing_values,
        "numeric_summary": numeric_summary,
        "bar_chart": grouped_chart or fallback_chart,
        "sample_rows": sample_rows,
    }
def _build_grouped_species_chart(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    numeric_summary: dict[str, dict[str, float | int]],
) -> dict[str, Any] | None:
    normalized_fields = {field.casefold(): field for field in fieldnames}
    group_field = normalized_fields.get("species")
    if not group_field:
        return None

    series = [field for field in fieldnames if field in numeric_summary][:4]
    if not series:
        return None

    grouped_values: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        flower_name = (row.get(group_field) or "").strip()
        if not flower_name:
            continue

        metrics = grouped_values.setdefault(flower_name, {name: [] for name in series})
        for metric in series:
            raw_value = (row.get(metric) or "").strip()
            if not raw_value:
                continue
            try:
                metrics[metric].append(float(raw_value))
            except ValueError:
                continue

    groups = []
    for flower_name, metrics in grouped_values.items():
        averages = {
            metric: round(sum(values) / len(values), 2)
            for metric, values in metrics.items()
            if values
        }
        if averages:
            groups.append({"flower": flower_name, "averages": averages})

    if not groups:
        return None

    return {
        "kind": "grouped",
        "metric": "average",
        "x_axis": group_field,
        "series": series,
        "groups": groups,
    }


def _image_to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _preview_image(image: Image.Image) -> Image.Image:
    preview = image.copy()
    preview.thumbnail((640, 640))
    return preview


def _apply_transform(image: Image.Image, transform: ImageTransform) -> Image.Image:
    if transform == ImageTransform.THUMBNAIL:
        preview = image.copy()
        preview.thumbnail((320, 320))
        return preview

    if transform == ImageTransform.GRAYSCALE:
        preview = image.convert("L").convert("RGB")
        preview.thumbnail((320, 320))
        return preview

    if transform == ImageTransform.SEPIA:
        sepia = image.copy()
        sepia.thumbnail((320, 320))
        pixels = sepia.load()
        for y in range(sepia.height):
            for x in range(sepia.width):
                red, green, blue = pixels[x, y]
                pixels[x, y] = (
                    min(int((red * 0.393) + (green * 0.769) + (blue * 0.189)), 255),
                    min(int((red * 0.349) + (green * 0.686) + (blue * 0.168)), 255),
                    min(int((red * 0.272) + (green * 0.534) + (blue * 0.131)), 255),
                )
        return sepia

    if transform == ImageTransform.BLUR:
        preview = image.copy()
        preview.thumbnail((320, 320))
        return preview.filter(ImageFilter.GaussianBlur(radius=3))

    if transform == ImageTransform.EDGE_ENHANCE:
        preview = image.copy()
        preview.thumbnail((320, 320))
        return preview.filter(ImageFilter.EDGE_ENHANCE_MORE)

    raise ValueError(f"Unsupported image transform: {transform}")


def _transform_label(transform: ImageTransform) -> str:
    labels = {
        ImageTransform.THUMBNAIL: "Thumbnail",
        ImageTransform.GRAYSCALE: "Grayscale",
        ImageTransform.SEPIA: "Sepia",
        ImageTransform.BLUR: "Blur",
        ImageTransform.EDGE_ENHANCE: "Edge Enhance",
    }
    return labels[transform]


def _transform_description(transform: ImageTransform) -> str:
    descriptions = {
        ImageTransform.THUMBNAIL: "Resized preview optimized for quick scanning.",
        ImageTransform.GRAYSCALE: "Monochrome treatment that highlights tone and contrast.",
        ImageTransform.SEPIA: "Warm archival-style grade for a classic look.",
        ImageTransform.BLUR: "Softened version using a Gaussian blur.",
        ImageTransform.EDGE_ENHANCE: "Sharper edge-focused version for structure and detail.",
    }
    return descriptions[transform]

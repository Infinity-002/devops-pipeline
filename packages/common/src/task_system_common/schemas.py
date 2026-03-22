from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class TaskType(StrEnum):
    IMAGE_PROCESSING = "image_processing"
    CSV_ANALYSIS = "csv_analysis"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ImagePayload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    image_data_url: str = Field(min_length=32, max_length=12_000_000)


class CsvPayload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    csv_text: str = Field(min_length=1, max_length=2_000_000)

    @field_validator("csv_text")
    @classmethod
    def ensure_non_empty_csv_rows(cls, value: str) -> str:
        if not [line for line in value.splitlines() if line.strip()]:
            raise ValueError("csv_text must contain at least one non-empty row")
        return value


TaskPayload = ImagePayload | CsvPayload


class CreateTaskRequest(BaseModel):
    task_type: TaskType
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_payload(self) -> CreateTaskRequest:
        if self.task_type == TaskType.IMAGE_PROCESSING:
            ImagePayload.model_validate(self.payload)
        elif self.task_type == TaskType.CSV_ANALYSIS:
            CsvPayload.model_validate(self.payload)
        return self


class TaskRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: TaskType
    status: TaskStatus = TaskStatus.QUEUED
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskResponse(BaseModel):
    id: str
    task_type: TaskType
    status: TaskStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateTaskResponse(BaseModel):
    task_id: str
    status: Literal["queued"]

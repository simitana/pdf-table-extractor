from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TableOut(BaseModel):
    id: int
    page_number: int
    table_index: int
    headers: list[str]
    rows: list[list[Any]]
    row_count: int
    column_count: int
    confidence: float


class JobOut(BaseModel):
    id: str
    original_filename: str
    status: JobStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    table_count: int


class JobDetailOut(JobOut):
    tables: list[TableOut]


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus

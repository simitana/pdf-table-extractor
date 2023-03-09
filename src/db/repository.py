from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..core.exceptions import JobNotFoundError
from ..core.extraction import ExtractedTable
from ..core.models import JobDetailOut, JobOut, JobStatus, TableOut
from .connection import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRepository:
    def __init__(self, database: Database) -> None:
        self._db = database

    def create(self, original_filename: str, stored_filename: str) -> str:
        job_id = str(uuid.uuid4())
        timestamp = _now()
        with self._db.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (id, original_filename, stored_filename, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, original_filename, stored_filename, JobStatus.QUEUED, timestamp, timestamp),
            )
        return job_id

    def mark_processing(self, job_id: str) -> None:
        self._update_status(job_id, JobStatus.PROCESSING)

    def mark_completed(self, job_id: str, tables: list[ExtractedTable]) -> None:
        with self._db.connect() as connection:
            for table in tables:
                connection.execute(
                    """
                    INSERT INTO tables
                        (job_id, page_number, table_index, headers, rows, row_count, column_count, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        table.page_number,
                        table.table_index,
                        json.dumps(table.headers),
                        json.dumps(table.rows),
                        table.row_count,
                        table.column_count,
                        table.confidence,
                    ),
                )
            connection.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                (JobStatus.COMPLETED, _now(), job_id),
            )

    def mark_failed(self, job_id: str, error_message: str) -> None:
        with self._db.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (JobStatus.FAILED, error_message, _now(), job_id),
            )

    def _update_status(self, job_id: str, status: JobStatus) -> None:
        with self._db.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                (status, _now(), job_id),
            )

    def get(self, job_id: str) -> JobDetailOut:
        with self._db.connect() as connection:
            job_row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job_row is None:
                raise JobNotFoundError(job_id)
            table_rows = connection.execute(
                "SELECT * FROM tables WHERE job_id = ? ORDER BY page_number, table_index",
                (job_id,),
            ).fetchall()

        tables = [_row_to_table(row) for row in table_rows]
        fields = _row_to_job_fields(job_row)
        return JobDetailOut(**fields, table_count=len(tables), tables=tables)

    def get_stored_filename(self, job_id: str) -> str:
        with self._db.connect() as connection:
            row = connection.execute(
                "SELECT stored_filename FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise JobNotFoundError(job_id)
        return row["stored_filename"]

    def list_all(self) -> list[JobOut]:
        with self._db.connect() as connection:
            rows = connection.execute(
                """
                SELECT jobs.*, COUNT(tables.id) AS table_count
                FROM jobs
                LEFT JOIN tables ON tables.job_id = jobs.id
                GROUP BY jobs.id
                ORDER BY jobs.created_at DESC
                """
            ).fetchall()
        return [JobOut(**_row_to_job_fields(row), table_count=row["table_count"]) for row in rows]

    def delete(self, job_id: str) -> None:
        with self._db.connect() as connection:
            cursor = connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            if cursor.rowcount == 0:
                raise JobNotFoundError(job_id)


def _row_to_job_fields(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "original_filename": row["original_filename"],
        "status": row["status"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_table(row: Any) -> TableOut:
    return TableOut(
        id=row["id"],
        page_number=row["page_number"],
        table_index=row["table_index"],
        headers=json.loads(row["headers"]),
        rows=json.loads(row["rows"]),
        row_count=row["row_count"],
        column_count=row["column_count"],
        confidence=row["confidence"],
    )

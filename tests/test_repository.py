from __future__ import annotations

from pathlib import Path

import pytest

from src.core.exceptions import JobNotFoundError
from src.core.extraction import ExtractedTable
from src.db.connection import Database
from src.db.repository import JobRepository


@pytest.fixture
def repository(tmp_path: Path) -> JobRepository:
    database = Database(tmp_path / "test.db")
    return JobRepository(database)


def test_create_and_get_job(repository: JobRepository) -> None:
    job_id = repository.create("invoice.pdf", "abc123.pdf")
    job = repository.get(job_id)
    assert job.original_filename == "invoice.pdf"
    assert job.status == "queued"
    assert job.tables == []


def test_mark_completed_persists_tables(repository: JobRepository) -> None:
    job_id = repository.create("invoice.pdf", "abc123.pdf")
    tables = [
        ExtractedTable(page_number=1, table_index=0, headers=["a", "b"], rows=[["1", "2"]], confidence=0.9)
    ]
    repository.mark_completed(job_id, tables)
    job = repository.get(job_id)
    assert job.status == "completed"
    assert len(job.tables) == 1
    assert job.tables[0].headers == ["a", "b"]


def test_mark_failed_sets_error_message(repository: JobRepository) -> None:
    job_id = repository.create("invoice.pdf", "abc123.pdf")
    repository.mark_failed(job_id, "boom")
    job = repository.get(job_id)
    assert job.status == "failed"
    assert job.error_message == "boom"


def test_get_missing_job_raises(repository: JobRepository) -> None:
    with pytest.raises(JobNotFoundError):
        repository.get("does-not-exist")


def test_list_all_orders_by_created_at_desc(repository: JobRepository) -> None:
    first = repository.create("a.pdf", "a.pdf")
    second = repository.create("b.pdf", "b.pdf")
    jobs = repository.list_all()
    assert [job.id for job in jobs] == [second, first]


def test_delete_removes_job_and_tables(repository: JobRepository) -> None:
    job_id = repository.create("invoice.pdf", "abc123.pdf")
    repository.delete(job_id)
    with pytest.raises(JobNotFoundError):
        repository.get(job_id)


def test_delete_missing_job_raises(repository: JobRepository) -> None:
    with pytest.raises(JobNotFoundError):
        repository.delete("does-not-exist")

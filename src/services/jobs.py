from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from ..core.exceptions import ExtractionFailedError, FileTooLargeError, UnsupportedFileError
from ..core.extraction import extract_tables
from ..db.repository import JobRepository

ALLOWED_CONTENT_TYPES = {"application/pdf"}
CHUNK_SIZE = 1024 * 1024


class JobService:
    def __init__(self, repository: JobRepository, upload_dir: Path, max_upload_size_bytes: int) -> None:
        self._repository = repository
        self._upload_dir = upload_dir
        self._max_upload_size_bytes = max_upload_size_bytes

    async def submit(self, upload: UploadFile) -> str:
        self._validate(upload)

        stored_filename = f"{uuid.uuid4().hex}.pdf"
        destination = self._upload_dir / stored_filename

        size = 0
        with destination.open("wb") as buffer:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > self._max_upload_size_bytes:
                    buffer.close()
                    destination.unlink(missing_ok=True)
                    raise FileTooLargeError(upload.filename or stored_filename)
                buffer.write(chunk)

        return self._repository.create(upload.filename or stored_filename, stored_filename)

    def process(self, job_id: str) -> None:
        stored_filename = self._repository.get_stored_filename(job_id)
        pdf_path = self._upload_dir / stored_filename

        self._repository.mark_processing(job_id)
        try:
            tables = extract_tables(pdf_path)
        except ExtractionFailedError as exc:
            self._repository.mark_failed(job_id, str(exc))
            return
        self._repository.mark_completed(job_id, tables)

    def delete(self, job_id: str) -> None:
        stored_filename = self._repository.get_stored_filename(job_id)
        self._repository.delete(job_id)
        (self._upload_dir / stored_filename).unlink(missing_ok=True)

    def _validate(self, upload: UploadFile) -> None:
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedFileError(upload.content_type or "unknown")

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response

from ..core.exceptions import FileTooLargeError, JobNotFoundError, UnsupportedFileError
from ..core.models import JobDetailOut, JobOut, JobStatus, UploadResponse
from ..db.repository import JobRepository
from ..services import export
from ..services.jobs import JobService
from .deps import get_job_service, get_repository

router = APIRouter(prefix="/api")


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    job_service: JobService = Depends(get_job_service),
) -> UploadResponse:
    try:
        job_id = await job_service.submit(file)
    except UnsupportedFileError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc

    background_tasks.add_task(job_service.process, job_id)
    return UploadResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.get("/job/{job_id}/status", response_model=JobOut)
def get_job_status(job_id: str, repository: JobRepository = Depends(get_repository)) -> JobOut:
    return _get_job_or_404(job_id, repository)


@router.get("/job/{job_id}/tables", response_model=JobDetailOut)
def get_job_tables(job_id: str, repository: JobRepository = Depends(get_repository)) -> JobDetailOut:
    return _get_job_or_404(job_id, repository)


@router.get("/job/{job_id}/export/csv")
def export_csv(
    job_id: str, table_id: int, repository: JobRepository = Depends(get_repository)
) -> Response:
    job = _get_job_or_404(job_id, repository)
    table = next((t for t in job.tables if t.id == table_id), None)
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "table not found")
    content = export.to_csv(table)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=job_{job_id}_table_{table_id}.csv"},
    )


@router.get("/job/{job_id}/export/xlsx")
def export_xlsx(job_id: str, repository: JobRepository = Depends(get_repository)) -> Response:
    job = _get_job_or_404(job_id, repository)
    if not job.tables:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no tables extracted")
    content = export.to_excel(job.tables)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=job_{job_id}.xlsx"},
    )


@router.get("/history", response_model=list[JobOut])
def get_history(repository: JobRepository = Depends(get_repository)) -> list[JobOut]:
    return repository.list_all()


@router.delete("/job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, job_service: JobService = Depends(get_job_service)) -> None:
    try:
        job_service.delete(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _get_job_or_404(job_id: str, repository: JobRepository) -> JobDetailOut:
    try:
        return repository.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

from __future__ import annotations

from fastapi import Request

from ..db.repository import JobRepository
from ..services.jobs import JobService


def get_repository(request: Request) -> JobRepository:
    return request.app.state.repository


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service

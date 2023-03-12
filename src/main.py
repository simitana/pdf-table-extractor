from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import settings
from .db.connection import Database
from .db.repository import JobRepository
from .logging_config import configure_logging
from .services.jobs import JobService

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database = Database(settings.database_path)
    repository = JobRepository(database)
    app.state.repository = repository
    app.state.job_service = JobService(repository, settings.upload_dir, settings.max_upload_size_bytes)
    logger.info("application startup complete")
    yield
    logger.info("application shutdown")


app = FastAPI(title="PDF Table Extractor", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

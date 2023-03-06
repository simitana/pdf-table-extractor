from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    upload_dir: Path
    database_path: Path
    max_upload_size_bytes: int
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        base_dir = Path(__file__).resolve().parent.parent
        upload_dir = Path(os.getenv("UPLOAD_DIR", base_dir / "uploads"))
        database_path = Path(os.getenv("DATABASE_PATH", base_dir / "data" / "extractor.db"))
        max_upload_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        upload_dir.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            upload_dir=upload_dir,
            database_path=database_path,
            max_upload_size_bytes=max_upload_size_mb * 1024 * 1024,
            log_level=log_level,
        )


settings = Settings.from_env()

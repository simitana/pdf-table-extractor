from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "data" / "extractor.db"))

    import src.config as config_module
    import src.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client

from __future__ import annotations

import io
import time

from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table


def _build_sample_pdf() -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter)
    data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "Lisbon"],
        ["Bob", "25", "Porto"],
    ]
    document.build([Table(data)])
    return buffer.getvalue()


def _wait_until_completed(client: TestClient, job_id: str) -> dict:
    for _ in range(20):
        response = client.get(f"/api/job/{job_id}/status")
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.1)
    raise TimeoutError("job did not finish in time")


def test_upload_and_process_pdf(client: TestClient) -> None:
    pdf_bytes = _build_sample_pdf()
    response = client.post("/api/upload", files={"file": ("sample.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_payload = _wait_until_completed(client, job_id)
    assert status_payload["status"] == "completed"

    tables_response = client.get(f"/api/job/{job_id}/tables")
    tables = tables_response.json()["tables"]
    assert len(tables) == 1
    assert tables[0]["headers"] == ["Name", "Age", "City"]


def test_upload_rejects_non_pdf(client: TestClient) -> None:
    response = client.post("/api/upload", files={"file": ("sample.txt", b"hello", "text/plain")})
    assert response.status_code == 415


def test_export_csv_and_xlsx(client: TestClient) -> None:
    pdf_bytes = _build_sample_pdf()
    upload = client.post("/api/upload", files={"file": ("sample.pdf", pdf_bytes, "application/pdf")})
    job_id = upload.json()["job_id"]
    _wait_until_completed(client, job_id)

    tables = client.get(f"/api/job/{job_id}/tables").json()["tables"]
    table_id = tables[0]["id"]

    csv_response = client.get(f"/api/job/{job_id}/export/csv", params={"table_id": table_id})
    assert csv_response.status_code == 200
    assert b"Alice" in csv_response.content

    xlsx_response = client.get(f"/api/job/{job_id}/export/xlsx")
    assert xlsx_response.status_code == 200
    assert xlsx_response.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_history_lists_jobs(client: TestClient) -> None:
    pdf_bytes = _build_sample_pdf()
    upload = client.post("/api/upload", files={"file": ("sample.pdf", pdf_bytes, "application/pdf")})
    job_id = upload.json()["job_id"]
    _wait_until_completed(client, job_id)

    history = client.get("/api/history").json()
    assert any(job["id"] == job_id for job in history)


def test_delete_job_removes_it(client: TestClient) -> None:
    pdf_bytes = _build_sample_pdf()
    upload = client.post("/api/upload", files={"file": ("sample.pdf", pdf_bytes, "application/pdf")})
    job_id = upload.json()["job_id"]
    _wait_until_completed(client, job_id)

    delete_response = client.delete(f"/api/job/{job_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/job/{job_id}/status")
    assert missing_response.status_code == 404


def test_export_csv_missing_table_returns_404(client: TestClient) -> None:
    pdf_bytes = _build_sample_pdf()
    upload = client.post("/api/upload", files={"file": ("sample.pdf", pdf_bytes, "application/pdf")})
    job_id = upload.json()["job_id"]
    _wait_until_completed(client, job_id)

    response = client.get(f"/api/job/{job_id}/export/csv", params={"table_id": 999})
    assert response.status_code == 404

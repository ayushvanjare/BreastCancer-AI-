import os
import tempfile
from fastapi.testclient import TestClient

# Use an isolated DB before importing the app.
tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"
os.environ["APP_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-tests"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

def auth_headers():
    import uuid
    suffix = uuid.uuid4().hex[:10]
    response = client.post("/api/auth/register", json={
        "email": f"{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "a-long-test-password-123",
    })
    assert response.status_code == 201, response.text
    token_response = client.post("/api/auth/login", data={
        "username": f"user_{suffix}",
        "password": "a-long-test-password-123",
    })
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}

def test_health_and_modules():
    assert client.get("/api/health").status_code == 200
    data = client.get("/api/modules").json()["modules"]
    assert len(data) == 6
    assert {m["id"] for m in data} == {"histopathology", "ct", "mri", "xray", "reports", "csv"}

def test_register_login_and_me():
    import uuid
    suffix = uuid.uuid4().hex[:10]
    r = client.post("/api/auth/register", json={
        "email": f"{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "a-long-test-password-123",
    })
    assert r.status_code == 201, r.text
    login = client.post("/api/auth/login", data={
        "username": f"user_{suffix}",
        "password": "a-long-test-password-123",
    })
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == f"user_{suffix}"

def test_analysis_does_not_fake_prediction():
    reg = client.post("/api/auth/register", json={
        "email": "analysis-test@example.com",
        "username": "analysis_test",
        "password": "a-long-test-password-123",
    })
    # If a prior test run left this user, log in instead.
    if reg.status_code == 409:
        login = client.post("/api/auth/login", data={
            "username": "analysis_test",
            "password": "a-long-test-password-123",
        })
        token = login.json()["access_token"]
    else:
        token = client.post("/api/auth/login", data={
            "username": "analysis_test",
            "password": "a-long-test-password-123",
        }).json()["access_token"]
    response = client.post("/api/analysis", json={"module_id": "histopathology"},
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_or_pipeline_unavailable"

def test_csv_analysis_returns_descriptive_summary():
    headers = auth_headers()
    response = client.post("/api/csv/analyze", files={
        "file": ("observations.csv", "age,group,score\n30,A,2\n40,B,4\n, A,6\n", "text/csv")
    }, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["analysis_type"] == "descriptive_statistics"
    assert data["shape"] == {"rows": 3, "columns": 3}
    assert data["columns"][0]["dtype"].startswith("float")
    assert data["columns"][0]["missing"] == 1
    assert data["descriptive_statistics"]["score"]["mean"] == 4
    assert data["chart_data"]["categorical"][0]["column"] == "group"

def test_csv_upload_rejects_wrong_type_and_malformed_data():
    headers = auth_headers()
    wrong_type = client.post("/api/csv/analyze", files={"file": ("data.txt", "x\n1\n", "text/plain")}, headers=headers)
    assert wrong_type.status_code == 415
    malformed = client.post("/api/csv/analyze", files={"file": ("data.csv", "a,b\n1,2,3\n", "text/csv")}, headers=headers)
    assert malformed.status_code == 400
    assert "found 3 fields" in malformed.json()["detail"]

def test_csv_analysis_supports_semicolon_and_short_rows():
    headers = auth_headers()
    response = client.post("/api/csv/analyze", files={
        "file": ("observations.csv", "name;score\nA;2\nB\n", "text/csv")
    }, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["shape"] == {"rows": 2, "columns": 2}
    assert data["columns"][1]["missing"] == 1

def test_csv_upload_rejects_oversize_file():
    headers = auth_headers()
    response = client.post("/api/csv/analyze", files={
        "file": ("large.csv", b"x" * (10 * 1024 * 1024 + 1), "text/csv")
    }, headers=headers)
    assert response.status_code == 413

def test_histopathology_model_endpoint_is_honest_when_unconfigured(monkeypatch):
    headers = auth_headers()
    monkeypatch.setattr(settings, "research_model_python", None)
    monkeypatch.setattr(settings, "histopathology_checkpoint", None)
    response = client.post("/api/research/histopathology/predict", files={
        "file": ("sample.png", b"not-an-image", "image/png"),
    }, headers=headers)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "research_model_unavailable"
    assert response.json()["detail"]["clinical_use"] is False

def test_histopathology_model_endpoint_rejects_unsupported_file(monkeypatch, tmp_path):
    headers = auth_headers()
    configured_path = tmp_path / "python.exe"
    configured_checkpoint = tmp_path / "model.pt"
    configured_path.write_bytes(b"configured for endpoint validation")
    configured_checkpoint.write_bytes(b"configured for endpoint validation")
    monkeypatch.setattr(settings, "research_model_python", str(configured_path))
    monkeypatch.setattr(settings, "histopathology_checkpoint", str(configured_checkpoint))
    response = client.post("/api/research/histopathology/predict", files={
        "file": ("sample.csv", b"x,y\n1,2\n", "text/csv"),
    }, headers=headers)
    assert response.status_code == 415

def test_configured_histopathology_worker_smoke_with_generated_image():
    import pytest
    from io import BytesIO
    from pathlib import Path
    from PIL import Image

    if not (settings.research_model_python and Path(settings.research_model_python).is_file()
            and settings.histopathology_checkpoint and Path(settings.histopathology_checkpoint).is_file()):
        pytest.skip("No local research-model Python/checkpoint paths are configured.")
    image_buffer = BytesIO()
    Image.new("RGB", (32, 32), color="white").save(image_buffer, format="PNG")
    headers = auth_headers()
    response = client.post("/api/research/histopathology/predict", files={
        "file": ("generated-smoke.png", image_buffer.getvalue(), "image/png"),
    }, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["analysis_type"] == "research_only_model_output"
    assert result["clinical_use"] is False
    assert result["execution_device"] in {"cpu", "cuda"}
    assert client.delete(f"/api/history/{result['history_id']}", headers=headers).status_code == 204

def test_imaging_review_returns_only_raster_metadata():
    headers = auth_headers()
    from io import BytesIO
    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (32, 24), color="white").save(image_buffer, format="PNG")
    response = client.post("/api/imaging/inspect", data={"module_id": "ct"}, files={
        "file": ("sample.png", image_buffer.getvalue(), "image/png"),
    }, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["inspection_type"] == "raster_image_metadata"
    assert result["metadata"]["width"] == 32
    assert result["metadata"]["height"] == 24
    assert result["modality_check"] == "not_verifiable_from_raster_image"
    assert result["patient_identifiers_returned"] is False
    assert result["model_inference_performed"] is False

def test_imaging_review_rejects_unsupported_files():
    headers = auth_headers()
    response = client.post("/api/imaging/inspect", data={"module_id": "mri"}, files={
        "file": ("scan.nii", b"not-supported", "application/octet-stream"),
    }, headers=headers)
    assert response.status_code == 400
    assert "not a readable NIfTI" in response.json()["detail"]

def _make_test_dicom(series_uid: str, instance_uid: str, z_position: float, study_uid: str | None = None) -> bytes:
    from io import BytesIO
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

    metadata = FileMetaDataset()
    metadata.MediaStorageSOPClassUID = CTImageStorage
    metadata.MediaStorageSOPInstanceUID = instance_uid
    metadata.TransferSyntaxUID = ExplicitVRLittleEndian
    metadata.ImplementationClassUID = generate_uid()
    dataset = FileDataset(None, {}, file_meta=metadata, preamble=b"\0" * 128)
    dataset.SOPClassUID = CTImageStorage
    dataset.SOPInstanceUID = instance_uid
    dataset.StudyInstanceUID = study_uid or generate_uid()
    dataset.SeriesInstanceUID = series_uid
    dataset.Modality = "CT"
    dataset.Rows = 16
    dataset.Columns = 16
    dataset.ImagePositionPatient = [0, 0, z_position]
    dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    output = BytesIO()
    dataset.save_as(output, enforce_file_format=True)
    return output.getvalue()

def test_dicom_series_review_checks_series_and_saves_originals():
    from pydicom.uid import generate_uid

    headers = auth_headers()
    series_uid = generate_uid()
    study_uid = generate_uid()
    first = _make_test_dicom(series_uid, generate_uid(), 0, study_uid)
    second = _make_test_dicom(series_uid, generate_uid(), 1, study_uid)
    response = client.post("/api/imaging/series/inspect", data={"module_id": "ct"}, files=[
        ("files", ("one.dcm", first, "application/dicom")),
        ("files", ("two.dcm", second, "application/dicom")),
    ], headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["inspection_type"] == "dicom_series_header_metadata"
    assert result["metadata"]["instances"] == 2
    assert result["pixel_data_read"] is False
    assert client.get(f"/api/history/{result['history_id']}/file", headers=headers).content.startswith(b"PK")

def test_dicom_series_review_rejects_mixed_series():
    from pydicom.uid import generate_uid

    headers = auth_headers()
    first = _make_test_dicom(generate_uid(), generate_uid(), 0)
    second = _make_test_dicom(generate_uid(), generate_uid(), 1)
    response = client.post("/api/imaging/series/inspect", data={"module_id": "ct"}, files=[
        ("files", ("one.dcm", first, "application/dicom")),
        ("files", ("two.dcm", second, "application/dicom")),
    ], headers=headers)
    assert response.status_code == 400
    assert "multiple DICOM series" in response.json()["detail"]

def test_nifti_header_review_only():
    import gzip
    import nibabel as nib
    import numpy as np

    headers = auth_headers()
    sample = nib.Nifti1Image(np.zeros((8, 9, 10), dtype=np.uint8), np.eye(4)).to_bytes()
    response = client.post("/api/imaging/inspect", data={"module_id": "mri"}, files={
        "file": ("volume.nii", sample, "application/octet-stream"),
    }, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["inspection_type"] == "nifti_header_metadata"
    assert result["metadata"]["dimensions"] == [8, 9, 10]
    assert result["model_inference_performed"] is False
    compressed = client.post("/api/imaging/inspect", data={"module_id": "mri"}, files={
        "file": ("volume.nii.gz", gzip.compress(sample), "application/gzip"),
    }, headers=headers)
    assert compressed.status_code == 200, compressed.text
    assert compressed.json()["metadata"]["dimensions"] == [8, 9, 10]

def test_report_extraction_reads_embedded_pdf_text_in_memory():
    headers = auth_headers()
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Research report example text")
    pdf_bytes = document.tobytes()
    document.close()
    response = client.post("/api/reports/extract", files={
        "file": ("sample.pdf", pdf_bytes, "application/pdf"),
    }, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["method"] == "embedded_text"
    assert result["pages"] == 1
    assert result["character_count"] == len(result["text"])
    assert "Research report example text" in result["text"]
    history = client.get(f"/api/history/{result['history_id']}", headers=headers)
    assert history.status_code == 200
    assert "Research report example text" in history.json()["result"]["text"]

def test_report_extraction_rejects_wrong_type_and_invalid_pdf():
    headers = auth_headers()
    wrong_type = client.post("/api/reports/extract", files={
        "file": ("notes.txt", b"text", "text/plain"),
    }, headers=headers)
    assert wrong_type.status_code == 415
    invalid_pdf = client.post("/api/reports/extract", files={
        "file": ("notes.pdf", b"not a PDF", "application/pdf"),
    }, headers=headers)
    assert invalid_pdf.status_code == 400

def test_report_extraction_rejects_oversize_upload():
    headers = auth_headers()
    response = client.post("/api/reports/extract", files={
        "file": ("large.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024), "application/pdf"),
    }, headers=headers)
    assert response.status_code == 413

def test_uploads_require_login():
    response = client.post("/api/csv/analyze", files={"file": ("data.csv", "x\n1\n", "text/csv")})
    assert response.status_code == 401

def test_history_is_encrypted_account_scoped_and_deletable():
    owner = auth_headers()
    outsider = auth_headers()
    payload = b"secret,research\n1,2\n"
    response = client.post("/api/csv/analyze", files={"file": ("private.csv", payload, "text/csv")}, headers=owner)
    assert response.status_code == 200, response.text
    record_id = response.json()["history_id"]
    assert client.get("/api/history", headers=owner).json()["items"][0]["id"] == record_id
    assert client.get(f"/api/history/{record_id}", headers=owner).json()["result"]["shape"] == {"rows": 1, "columns": 2}
    assert client.get(f"/api/history/{record_id}/file", headers=owner).content == payload
    assert client.get(f"/api/history/{record_id}", headers=outsider).status_code == 404
    from app.database import SessionLocal
    from app.models import AnalysisHistory
    with SessionLocal() as db:
        record = db.query(AnalysisHistory).filter(AnalysisHistory.id == record_id).one()
        assert payload not in record.encrypted_upload
        assert b"private.csv" not in record.encrypted_result
    assert client.delete(f"/api/history/{record_id}", headers=owner).status_code == 204
    assert client.get("/api/history", headers=owner).json()["items"] == []

def test_history_routes_require_authentication():
    assert client.get("/api/history").status_code == 401
    assert client.get("/api/history/1").status_code == 401
    assert client.get("/api/history/1/file").status_code == 401
    assert client.delete("/api/history/1").status_code == 401

def test_history_file_and_delete_are_account_scoped():
    owner = auth_headers()
    outsider = auth_headers()
    payload = b"private upload,owner only\n"
    created = client.post("/api/csv/analyze", files={
        "file": ("private.csv", payload, "text/csv")
    }, headers=owner)
    assert created.status_code == 200, created.text
    record_id = created.json()["history_id"]

    assert client.get(f"/api/history/{record_id}/file", headers=outsider).status_code == 404
    assert client.delete(f"/api/history/{record_id}", headers=outsider).status_code == 404
    assert client.get(f"/api/history/{record_id}/file", headers=owner).content == payload
    assert [item["id"] for item in client.get("/api/history", headers=owner).json()["items"]] == [record_id]

def test_failed_upload_does_not_create_history_record():
    headers = auth_headers()
    malformed = client.post("/api/csv/analyze", files={
        "file": ("bad.csv", "a,b\n1,2,3\n", "text/csv")
    }, headers=headers)
    assert malformed.status_code == 400
    assert client.get("/api/history", headers=headers).json()["items"] == []

def test_module_registry_reports_existing_paths_as_unverified(monkeypatch, tmp_path):
    from app.config import settings

    python_path = tmp_path / "python.exe"
    checkpoint_path = tmp_path / "checkpoint.pt"
    python_path.write_bytes(b"placeholder")
    checkpoint_path.write_bytes(b"placeholder")
    monkeypatch.setattr(settings, "research_model_python", str(python_path))
    monkeypatch.setattr(settings, "histopathology_checkpoint", str(checkpoint_path))

    response = client.get("/api/modules")
    module = next(item for item in response.json()["modules"] if item["id"] == "histopathology")
    assert module["status"] == "research_model_paths_set_unverified"
    assert "have not been verified" in module["description"]

def test_module_registry_reports_included_checkpoints_as_unverified(monkeypatch):
    monkeypatch.setattr(settings, "research_model_python", None)
    monkeypatch.setattr(settings, "histopathology_checkpoint", None)
    response = client.get("/api/modules")
    module = next(item for item in response.json()["modules"] if item["id"] == "histopathology")
    assert module["available_checkpoints"] == 20
    assert module["status"] == "research_checkpoints_present_unverified"
    assert "runtime is unverified" in module["description"].lower()

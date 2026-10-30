import base64
import json
import logging
import subprocess
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import Response
from sqlalchemy.orm import Session

from .catalog import MODULES
from .config import settings
from .database import Base, engine, get_db
from .models import AnalysisHistory, User
from .schemas import AnalysisRequest, RegisterRequest, TokenResponse, UserResponse
from .security import create_access_token, decode_access_token, hash_password, verify_password
from .csv_analysis import analyze_csv
from .imaging_review import inspect_imaging_input, inspect_dicom_series, ImagingReviewError, ImagingReviewUnavailableError
from .report_extraction import extract_report, ReportExtractionError, OCRUnavailableError
from .history_storage import HistoryStorageError, SqliteEncryptedHistoryStore, decrypt_bytes, decrypt_json
from .research_inputs import preflight_brca_csv

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Local-first BreastCare AI research platform. Optional histopathology model outputs and imaging metadata reviews are research-only; CSV analysis is descriptive and reports are text-extracted only.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
MAX_CSV_BYTES = 50 * 1024 * 1024
MAX_REPORT_BYTES = 25 * 1024 * 1024
MAX_HISTOPATHOLOGY_BYTES = 50 * 1024 * 1024
MAX_IMAGING_BYTES = 50 * 1024 * 1024
MAX_NIFTI_BYTES = 500 * 1024 * 1024
MAX_DICOM_SERIES_BYTES = 250 * 1024 * 1024
logger = logging.getLogger(__name__)

@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "phase": "research-prototype", "database": "configured"}

def _included_histopathology_checkpoints():
    model_root = Path(__file__).resolve().parents[2] / "model_artifacts" / "breakhis"
    checkpoint_files = [*model_root.glob("resnet18/fold*_*x/*.pt"), *model_root.glob("baseline/fold*_*x/*.pt")]
    entries = []
    for checkpoint in sorted(checkpoint_files):
        relative = checkpoint.relative_to(model_root)
        folder = checkpoint.parent.name
        magnification = folder.rsplit("_", 1)[-1].removesuffix("x").upper() + "X"
        architecture = "ResNet-18" if relative.parts[0] == "resnet18" else "Scratch CNN baseline"
        entries.append({"id": relative.with_suffix("").as_posix(), "fold": folder.split("_")[0],
                        "magnification": magnification, "architecture": architecture, "path": checkpoint})
    return model_root, entries

@app.get("/api/modules")
def list_modules():
    modules = [dict(module) for module in MODULES]
    _model_root, checkpoints = _included_histopathology_checkpoints()
    checkpoint_count = sum(item["architecture"] == "ResNet-18" for item in checkpoints)
    histopathology = next(module for module in modules if module["id"] == "histopathology")
    histopathology["available_checkpoints"] = checkpoint_count
    histopathology["available_baselines"] = sum(item["architecture"] == "Scratch CNN baseline" for item in checkpoints)
    histopathology["checkpoints"] = [{key: item[key] for key in ("id", "fold", "magnification", "architecture")} for item in checkpoints]
    python_path = Path(settings.research_model_python).expanduser() if settings.research_model_python else None
    checkpoint_path = Path(settings.histopathology_checkpoint).expanduser() if settings.histopathology_checkpoint else None
    paths_set = bool(python_path and python_path.is_file() and ((checkpoint_path and checkpoint_path.is_file()) or checkpoints))
    if paths_set:
        histopathology["status"] = "research_model_paths_set_unverified"
        histopathology["description"] = "Python and checkpoint paths exist; runtime compatibility and inference have not been verified. Research-only; not for diagnosis or clinical use."
    elif checkpoints:
        histopathology["status"] = "research_checkpoints_present_unverified"
        histopathology["description"] = f"{len(checkpoints)} local BreaKHis research checkpoints are included, but no compatible inference runtime is configured. Runtime is unverified; not for diagnosis or clinical use."
    return {"modules": modules}

@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    username = payload.username.strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="This username is already taken.")
    user = User(email=email, username=username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, email=user.email, username=user.username)

@app.post("/api/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identity = form.username.strip()
    user = db.query(User).filter(
        (User.email == identity.lower()) | (User.username == identity)
    ).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password.")
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.token_ttl_hours * 3600,
    )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return user

@app.post("/api/research/brca/preflight")
async def brca_cohort_preflight(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Validate aggregate schema/labels of a de-identified BRCA cohort CSV in memory."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Choose a CSV cohort file.")
    content = await file.read(50 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="BRCA cohort preflight is limited to 50 MB.")
    try:
        return preflight_brca_csv(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, username=user.username)


def _history_store(db: Session) -> SqliteEncryptedHistoryStore:
    return SqliteEncryptedHistoryStore(db)


def _save_history(db: Session, user: User, analysis_type: str, filename: str,
                  content_type: str | None, content: bytes, result: dict) -> AnalysisHistory:
    try:
        return _history_store(db).save(user.id, analysis_type, filename, content_type, content, result)
    except HistoryStorageError as exc:
        logger.exception("Could not persist encrypted analysis history")
        raise HTTPException(status_code=500, detail="Analysis completed, but the encrypted history entry could not be saved.") from exc


def _owned_history_record(db: Session, user: User, record_id: int) -> AnalysisHistory:
    record = _history_store(db).get_for_user(user.id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return record


@app.get("/api/history")
def list_analysis_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = _history_store(db).list_for_user(user.id)
    return {"items": [{
        "id": record.id,
        "analysis_type": record.analysis_type,
        "filename": record.filename,
        "content_type": record.content_type,
        "size_bytes": record.size_bytes,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    } for record in records]}


@app.get("/api/history/{record_id}")
def get_analysis_history(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = _owned_history_record(db, user, record_id)
    try:
        result = decrypt_json(record.encrypted_result)
    except HistoryStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"id": record.id, "analysis_type": record.analysis_type, "filename": record.filename,
            "created_at": record.created_at.isoformat() if record.created_at else None, "result": result}


@app.get("/api/history/{record_id}/file")
def download_history_file(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from urllib.parse import quote
    record = _owned_history_record(db, user, record_id)
    try:
        content = decrypt_bytes(record.encrypted_upload)
    except HistoryStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(content=content, media_type=record.content_type,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.filename)}"})


@app.delete("/api/history/{record_id}", status_code=204)
def delete_analysis_history(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        deleted = _history_store(db).delete_for_user(user.id, record_id)
    except HistoryStorageError as exc:
        logger.exception("Could not delete encrypted analysis history")
        raise HTTPException(status_code=500, detail="Could not delete this history entry.") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return Response(status_code=204)
@app.post("/api/analysis")
def create_analysis(payload: AnalysisRequest, user: User = Depends(get_current_user)):
    module = next((m for m in MODULES if m["id"] == payload.module_id), None)
    if module is None:
        raise HTTPException(status_code=422, detail="Unknown module_id.")
    # Phase 1 deliberately does not fabricate inference. The endpoint is a truthful readiness check.
    raise HTTPException(
        status_code=503,
        detail={
            "code": "model_or_pipeline_unavailable",
            "message": "This endpoint does not provide inference. Use the module's implemented descriptive workflow or configure a compatible research model where available.",
            "module_id": payload.module_id,
            "module_status": module["status"],
            "next_step": "Install or implement a compatible pipeline and validated model before requesting analysis.",
        },
    )


@app.post("/api/research/histopathology/predict")
def predict_histopathology(file: UploadFile = File(...), explain: bool = Form(False), checkpoint_id: str | None = Form(None),
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run an optional local BreaKHis research checkpoint. This is not diagnostic."""
    python_path = Path(settings.research_model_python).expanduser() if settings.research_model_python else None
    checkpoint_root, included_checkpoints = _included_histopathology_checkpoints()
    if checkpoint_id:
        selected_checkpoint = next((item for item in included_checkpoints if item["id"] == checkpoint_id), None)
        if not selected_checkpoint:
            raise HTTPException(status_code=422, detail="Choose one of the included BreaKHis checkpoints.")
        checkpoint_path = selected_checkpoint["path"]
    else:
        checkpoint_path = Path(settings.histopathology_checkpoint).expanduser() if settings.histopathology_checkpoint else None
    if not python_path or not python_path.is_file() or (not checkpoint_id and (not checkpoint_path or not checkpoint_path.is_file())):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "research_model_unavailable",
                "message": "Configure a compatible local PyTorch Python environment to enable this research workflow.",
                "clinical_use": False,
            },
        )
    filename = (file.filename or "").strip()
    suffix = Path(filename).suffix.lower()
    accepted_types = {
        ".png": {"image/png", "application/octet-stream"},
        ".jpg": {"image/jpeg", "application/octet-stream"},
        ".jpeg": {"image/jpeg", "application/octet-stream"},
        ".tif": {"image/tiff", "application/octet-stream"},
        ".tiff": {"image/tiff", "application/octet-stream"},
    }
    if suffix not in accepted_types:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPG, JPEG, or TIFF histopathology image.")
    if file.content_type not in (None, "", *accepted_types[suffix]):
        raise HTTPException(status_code=415, detail="The uploaded content type does not match the image extension.")
    content = file.file.read(MAX_HISTOPATHOLOGY_BYTES + 1)
    file.file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The image file is empty.")
    if len(content) > MAX_HISTOPATHOLOGY_BYTES:
        raise HTTPException(status_code=413, detail="Image files must be 50 MB or smaller.")
    try:
        from PIL import Image, UnidentifiedImageError
        from io import BytesIO
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > 100_000_000:
                raise HTTPException(status_code=413, detail="The image dimensions exceed the supported limit.")
            image.verify()
    except HTTPException:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="The selected file is not a readable PNG, JPG, or TIFF image.") from exc

    worker_path = Path(__file__).with_name("research_model_worker.py")
    payload = json.dumps({"image_base64": base64.b64encode(content).decode("ascii"), "explain": explain})
    try:
        completed = subprocess.run(
            [str(python_path), str(worker_path), str(checkpoint_path)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="The local research model took too long to respond.") from exc
    except OSError as exc:
        logger.exception("Could not start the configured research model worker")
        raise HTTPException(status_code=503, detail="Could not start the configured local research model environment.") from exc
    if completed.returncode != 0:
        logger.error("Research model worker failed: %s", completed.stderr[-2000:])
        try:
            worker_error = json.loads(completed.stdout).get("error")
        except (json.JSONDecodeError, AttributeError):
            worker_error = None
        raise HTTPException(status_code=503, detail=worker_error or "The research model could not process this image.")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Research model worker returned invalid output: %s", completed.stdout[-1000:])
        raise HTTPException(status_code=503, detail="The research model returned an unreadable response.") from exc
    response = {"filename": filename, "size_bytes": len(content), "analysis_type": "research_only_model_output", **result}
    record = _save_history(db, user, "histopathology", filename, file.content_type, content, response)
    return {**response, "history_id": record.id}


@app.post("/api/imaging/inspect")
def inspect_imaging_upload(module_id: str = Form(...), file: UploadFile = File(...),
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Inspect one radiology image or DICOM header. No pixel inference or diagnosis is performed."""
    if module_id not in {"ct", "mri", "xray"}:
        raise HTTPException(status_code=422, detail="module_id must be ct, mri, or xray.")
    filename = (file.filename or "").strip()
    suffix = Path(filename).suffix.lower()
    is_nifti = filename.lower().endswith((".nii", ".nii.gz"))
    accepted_types = {
        ".dcm": {"application/dicom", "application/octet-stream"},
        ".dicom": {"application/dicom", "application/octet-stream"},
        ".png": {"image/png", "application/octet-stream"},
        ".jpg": {"image/jpeg", "application/octet-stream"},
        ".jpeg": {"image/jpeg", "application/octet-stream"},
        ".tif": {"image/tiff", "application/octet-stream"},
        ".tiff": {"image/tiff", "application/octet-stream"},
        ".nii": {"application/octet-stream", "application/x-nifti", "application/gzip"},
        ".gz": {"application/octet-stream", "application/gzip", "application/x-gzip"},
    }
    if suffix not in accepted_types or (suffix == ".gz" and not is_nifti):
        raise HTTPException(status_code=415, detail="Upload one DICOM, NIfTI, PNG, JPG, JPEG, or TIFF image.")
    if file.content_type not in (None, "", *accepted_types[suffix]):
        raise HTTPException(status_code=415, detail="The uploaded content type does not match the file extension.")
    size_limit = MAX_NIFTI_BYTES if is_nifti else MAX_IMAGING_BYTES
    content = file.file.read(size_limit + 1)
    file.file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The selected image is empty.")
    if len(content) > size_limit:
        raise HTTPException(status_code=413, detail="DICOM and raster images must be 50 MB or smaller; NIfTI files must be 500 MB or smaller.")
    try:
        result = inspect_imaging_input(module_id, filename, content)
    except ImagingReviewUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ImagingReviewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response = {"size_bytes": len(content), **result}
    record = _save_history(db, user, module_id, filename, file.content_type, content, response)
    return {**response, "history_id": record.id}


@app.post("/api/imaging/series/inspect")
async def inspect_dicom_series_upload(module_id: str = Form(...), files: list[UploadFile] = File(...),
                                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check technical consistency of one DICOM series. No pixels or diagnosis."""
    if module_id not in {"ct", "mri", "xray"}:
        raise HTTPException(status_code=422, detail="module_id must be ct, mri, or xray.")
    if not files or len(files) > 500:
        raise HTTPException(status_code=413, detail="Select between 1 and 500 DICOM instances.")
    from io import BytesIO
    from zipfile import ZIP_STORED, ZipFile
    entries = []
    total_bytes = 0
    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, "w", compression=ZIP_STORED) as archive:
        for index, upload in enumerate(files, start=1):
            name = Path(upload.filename or "").name
            if Path(name).suffix.lower() not in {".dcm", ".dicom"}:
                raise HTTPException(status_code=415, detail="A DICOM series may contain only .dcm or .dicom files.")
            content = await upload.read(MAX_IMAGING_BYTES + 1)
            await upload.close()
            if not content:
                raise HTTPException(status_code=400, detail="A selected DICOM instance is empty.")
            if len(content) > MAX_IMAGING_BYTES:
                raise HTTPException(status_code=413, detail="Each DICOM instance must be 50 MB or smaller.")
            total_bytes += len(content)
            if total_bytes > MAX_DICOM_SERIES_BYTES:
                raise HTTPException(status_code=413, detail="A DICOM series may total at most 250 MB.")
            entries.append((name, content))
            archive.writestr(f"instance-{index:04d}{Path(name).suffix.lower()}", content)
    try:
        result = inspect_dicom_series(module_id, entries)
    except ImagingReviewUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ImagingReviewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    archive_bytes = archive_buffer.getvalue()
    response = {"size_bytes": total_bytes, **result}
    record = _save_history(db, user, module_id, "dicom-series.zip", "application/zip", archive_bytes, response)
    return {**response, "history_id": record.id}

@app.post("/api/csv/analyze")
async def analyze_csv_upload(file: UploadFile = File(...), user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Analyze tabular data descriptively. No prediction or diagnosis is performed."""
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a .csv file.")
    if file.content_type not in (None, "", "text/csv", "application/csv", "application/vnd.ms-excel", "text/plain", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="The uploaded file must have a CSV-compatible content type.")
    content = await file.read(MAX_CSV_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The CSV file is empty.")
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV files must be 50 MB or smaller.")
    try:
        result = analyze_csv(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response = {"filename": filename, "size_bytes": len(content), "analysis_type": "descriptive_statistics", **result}
    record = _save_history(db, user, "csv", filename, file.content_type, content, response)
    return {**response, "history_id": record.id}


@app.post("/api/reports/extract")
def extract_report_upload(file: UploadFile = File(...), user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Extract readable text from PDFs or images; this endpoint does not interpret content."""
    filename = (file.filename or "").strip()
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    allowed_types = {"pdf": {"application/pdf", "application/octet-stream"},
                     "png": {"image/png", "application/octet-stream"},
                     "jpg": {"image/jpeg", "application/octet-stream"},
                     "jpeg": {"image/jpeg", "application/octet-stream"},
                     "tif": {"image/tiff", "application/octet-stream"},
                     "tiff": {"image/tiff", "application/octet-stream"},
                     "bmp": {"image/bmp", "image/x-ms-bmp", "application/octet-stream"}}
    if suffix not in allowed_types:
        raise HTTPException(status_code=415, detail="Upload a PDF, PNG, JPG, JPEG, TIFF, or BMP file.")
    if file.content_type not in (None, "", *allowed_types[suffix]):
        raise HTTPException(status_code=415, detail="The uploaded content type does not match a supported report file.")
    content = file.file.read(MAX_REPORT_BYTES + 1)
    file.file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The report file is empty.")
    if len(content) > MAX_REPORT_BYTES:
        raise HTTPException(status_code=413, detail="Report files must be 25 MB or smaller.")
    try:
        result = extract_report(filename, content)
    except OCRUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ReportExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response = {"filename": filename, "size_bytes": len(content), "extraction_type": "text_extraction",
                "character_count": len(result["text"]), **result}
    record = _save_history(db, user, "reports", filename, file.content_type, content, response)
    return {**response, "history_id": record.id}



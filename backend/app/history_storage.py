"""Account-scoped history storage contract and encrypted SQLite adapter."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from .models import AnalysisHistory

KEY_PATH = Path(__file__).resolve().parents[1] / ".history.key"


class HistoryStorageError(RuntimeError):
    pass


class AnalysisHistoryStore(Protocol):
    """Replaceable persistence contract used by the API history workflows."""

    def save(self, user_id: int, analysis_type: str, filename: str,
             content_type: str | None, content: bytes, result: dict) -> AnalysisHistory: ...

    def list_for_user(self, user_id: int, limit: int = 200) -> list[AnalysisHistory]: ...

    def get_for_user(self, user_id: int, record_id: int) -> AnalysisHistory | None: ...

    def delete_for_user(self, user_id: int, record_id: int) -> bool: ...


def _fernet() -> Fernet:
    """Load or atomically create a local key, excluded from source control."""
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        key = KEY_PATH.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(key)
        try:
            os.chmod(KEY_PATH, 0o600)
        except OSError:
            pass
    try:
        return Fernet(key)
    except (TypeError, ValueError) as exc:
        raise HistoryStorageError("The local history encryption key is invalid. Restore the ignored .history.key file or clear the local history database.") from exc


def encrypt_bytes(value: bytes) -> bytes:
    return _fernet().encrypt(value)


def decrypt_bytes(value: bytes) -> bytes:
    try:
        return _fernet().decrypt(value)
    except InvalidToken as exc:
        raise HistoryStorageError("This history entry cannot be decrypted with the current local key.") from exc


def encrypt_json(value: dict) -> bytes:
    return encrypt_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))


def decrypt_json(value: bytes) -> dict:
    try:
        result = json.loads(decrypt_bytes(value))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryStorageError("The saved analysis result is damaged or unreadable.") from exc
    if not isinstance(result, dict):
        raise HistoryStorageError("The saved analysis result has an invalid format.")
    return result


class SqliteEncryptedHistoryStore:
    """Default local adapter; another adapter can implement AnalysisHistoryStore."""

    _ALLOWED_SUFFIXES = {
        ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
        ".dcm", ".dicom", ".nii", ".nii.gz", ".gz", ".zip",
    }

    def __init__(self, db: Session):
        self._db = db

    def save(self, user_id: int, analysis_type: str, filename: str,
             content_type: str | None, content: bytes, result: dict) -> AnalysisHistory:
        suffix = ".nii.gz" if filename.lower().endswith(".nii.gz") else Path(filename).suffix.lower()
        if suffix not in self._ALLOWED_SUFFIXES:
            suffix = ".bin"
        record = AnalysisHistory(
            user_id=user_id,
            analysis_type=analysis_type,
            # Never persist a user-supplied (possibly identifying) filename.
            filename=f"{analysis_type}-upload{suffix}",
            content_type=(content_type or "application/octet-stream")[:128],
            size_bytes=len(content),
            encrypted_upload=encrypt_bytes(content),
            encrypted_result=encrypt_json(result),
        )
        try:
            self._db.add(record)
            self._db.commit()
            self._db.refresh(record)
        except Exception as exc:
            self._db.rollback()
            raise HistoryStorageError("Could not persist encrypted analysis history.") from exc
        return record

    def list_for_user(self, user_id: int, limit: int = 200) -> list[AnalysisHistory]:
        return (self._db.query(AnalysisHistory)
                .filter(AnalysisHistory.user_id == user_id)
                .order_by(AnalysisHistory.created_at.desc())
                .limit(limit).all())

    def get_for_user(self, user_id: int, record_id: int) -> AnalysisHistory | None:
        return (self._db.query(AnalysisHistory)
                .filter(AnalysisHistory.id == record_id,
                        AnalysisHistory.user_id == user_id)
                .first())

    def delete_for_user(self, user_id: int, record_id: int) -> bool:
        record = self.get_for_user(user_id, record_id)
        if record is None:
            return False
        try:
            self._db.delete(record)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            raise HistoryStorageError("Could not delete encrypted analysis history.") from exc
        return True

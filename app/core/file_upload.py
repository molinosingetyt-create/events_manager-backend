"""Guardado de archivos en disco (uploads del API)."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import bad_request

settings = get_settings()

_ALLOWED_IMAGE_EXT = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp"},
)
_ALLOWED_PHOTO_EXT = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})
_ALLOWED_DOC_EXT = frozenset({".pdf", *_ALLOWED_IMAGE_EXT})
_ALLOWED_DOC_MIME_PREFIXES = ("image/", "application/pdf")


def validate_profile_photo_upload(upload: UploadFile) -> None:
    """Solo imágenes para foto del colaborador."""
    if not upload.filename:
        raise bad_request("Archivo sin nombre")
    ct = (upload.content_type or "").lower()
    if ct.startswith("image/"):
        return
    ext = Path(upload.filename).suffix.lower()
    if ext in _ALLOWED_PHOTO_EXT:
        return
    raise bad_request("Solo se permiten imágenes (JPEG, PNG, WebP o GIF).")


def validate_profile_document_upload(upload: UploadFile) -> None:
    """Imágenes o PDF para expediente del colaborador."""
    if not upload.filename:
        raise bad_request("Archivo sin nombre")
    ct = (upload.content_type or "").lower()
    if any(ct.startswith(p) for p in _ALLOWED_DOC_MIME_PREFIXES):
        return
    ext = Path(upload.filename).suffix.lower()
    if ext in _ALLOWED_DOC_EXT:
        return
    raise bad_request("Solo se permiten imágenes (JPEG, PNG, etc.) o PDF.")


async def save_upload_file(upload: UploadFile) -> tuple[str, str, int]:
    """Guarda el archivo y devuelve (url_relativa, content_type, size_bytes)."""
    ext = Path(upload.filename or "").suffix[:16]
    name = f"{uuid.uuid4().hex}{ext}"
    base = Path(settings.upload_dir)
    base.mkdir(parents=True, exist_ok=True)
    dest = base / name
    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await upload.read(1024 * 64):
            written += len(chunk)
            if written > max_bytes:
                dest.unlink(missing_ok=True)
                raise bad_request("El archivo es demasiado grande")
            await out.write(chunk)
    ct = (upload.content_type or "application/octet-stream").lower()
    return f"/uploads/{name}", ct, written


async def save_profile_photo_file(
    upload: UploadFile,
    employee_id: int,
) -> tuple[str, str, int]:
    """Guarda foto en S3 si está configurado; si no, en disco local."""
    from app.core.s3_storage import s3_configured, upload_profile_photo

    validate_profile_photo_upload(upload)
    if s3_configured():
        return await upload_profile_photo(upload, employee_id)
    url, ct, size = await save_upload_file(upload)
    return url, ct, size

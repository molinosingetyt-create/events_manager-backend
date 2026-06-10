"""Carga de archivos a Amazon S3 (fotos de perfil del expediente)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.exceptions import bad_request

if TYPE_CHECKING:
    from fastapi import UploadFile

logger = logging.getLogger(__name__)


def s3_configured() -> bool:
    return bool(get_settings().s3_bucket.strip())


def _s3_client():
    import boto3

    settings = get_settings()
    kwargs: dict = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def _public_url(key: str) -> str:
    settings = get_settings()
    base = (settings.s3_public_base_url or "").strip().rstrip("/")
    if base:
        return f"{base}/{key.lstrip('/')}"
    bucket = settings.s3_bucket
    region = settings.aws_region
    if region == "us-east-1":
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _upload_bytes_sync(
    key: str,
    data: bytes,
    content_type: str,
) -> str:
    settings = get_settings()
    client = _s3_client()
    extra: dict = {"ContentType": content_type}
    if settings.s3_acl_public:
        extra["ACL"] = "public-read"
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        **extra,
    )
    return _public_url(key)


async def upload_bytes_to_s3(
    key: str,
    data: bytes,
    content_type: str,
) -> str:
    if not s3_configured():
        raise bad_request("Almacenamiento S3 no configurado en el servidor")
    return await asyncio.to_thread(_upload_bytes_sync, key, data, content_type)


async def upload_profile_photo(
    upload: UploadFile,
    employee_id: int,
) -> tuple[str, str, int]:
    """Lee el archivo, lo sube a S3 y devuelve (url_pública, content_type, size)."""
    if not upload.filename:
        raise bad_request("Archivo sin nombre")
    ext = Path(upload.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    settings = get_settings()
    prefix = settings.s3_profile_photos_prefix.strip("/")
    key = f"{prefix}/{employee_id}/{uuid.uuid4().hex}{ext}"
    max_bytes = settings.max_profile_photo_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(1024 * 64):
        total += len(chunk)
        if total > max_bytes:
            raise bad_request("La imagen es demasiado grande")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise bad_request("Archivo vacío")
    ct = (upload.content_type or "image/jpeg").lower()
    if not ct.startswith("image/"):
        ct = "image/jpeg"
    url = await upload_bytes_to_s3(key, data, ct)
    return url, ct, total

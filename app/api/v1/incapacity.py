import math
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.incapacity import (
    IncapacityCommentCreate,
    IncapacityCommentRead,
    IncapacityHistoryRead,
    IncapacityNoteCreate,
    IncapacityNoteRead,
    IncapacityNoteUpdate,
)
from app.schemas.overtime import UserBriefRead
from app.services import audit_service
from app.services import incapacity_service as svc

router = APIRouter()
settings = get_settings()


def _user_brief(u) -> UserBriefRead | None:
    if u is None:
        return None
    return UserBriefRead(id=u.id, name=u.name, email=u.email)


def _to_read(note) -> IncapacityNoteRead:
    hist_sorted = sorted(note.history_entries or [], key=lambda h: h.created_at)
    hist = [
        IncapacityHistoryRead(
            id=h.id,
            incapacity_id=h.incapacity_id,
            action=h.action,
            user_id=h.user_id,
            user=_user_brief(h.user),
            comment=h.comment,
            snapshot=h.snapshot,
            created_at=h.created_at,
        )
        for h in hist_sorted
    ]
    emp = note.employee
    employee_name = emp.name if emp is not None else ""
    return IncapacityNoteRead(
        id=note.id,
        employee_id=note.employee_id,
        employee_name=employee_name,
        type=note.type,
        description=note.description,
        support=note.support,
        start_date=note.start_date,
        end_date=note.end_date,
        file_url=note.file_url,
        created_by=note.created_by,
        creator=_user_brief(note.creator),
        status=note.status,
        created_at=note.created_at,
        updated_at=note.updated_at,
        history=hist,
    )


_ALLOWED_IMAGE_EXT = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".heic",
    ".heif",
    ".bmp",
)


def _validate_image_upload(upload: UploadFile) -> None:
    """Solo imágenes (soporte fotográfico / cámara móvil)."""
    from app.core.exceptions import bad_request

    ct = (upload.content_type or "").lower()
    if ct.startswith("image/"):
        return
    ext = Path(upload.filename or "").suffix.lower()
    if ext in _ALLOWED_IMAGE_EXT:
        return
    raise bad_request(
        "Solo se permiten imágenes (JPEG, PNG, WebP, HEIC, GIF, etc.).",
    )


async def _save_upload(upload: UploadFile) -> str:
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
                from app.core.exceptions import bad_request

                raise bad_request("El archivo es demasiado grande")
            await out.write(chunk)
    return f"/uploads/{name}"


@router.get("", response_model=PaginatedResponse[IncapacityNoteRead])
async def list_notes(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    employee_id: int | None = None,
    type: str | None = Query(None, alias="type_filter"),
) -> PaginatedResponse[IncapacityNoteRead]:
    items, total = await svc.list_notes(
        db,
        current,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        type_filter=type,
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.list",
        entity_type="incapacity_note",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_to_read(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=IncapacityNoteRead)
async def create_note(
    request: Request,
    body: IncapacityNoteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> IncapacityNoteRead:
    if current.role not in (
        Role.LEADER.value,
        Role.ADMIN.value,
        Role.HR.value,
        Role.MANAGEMENT.value,
    ):
        from app.core.exceptions import forbidden

        raise forbidden()
    n = await svc.create_note(db, current, body, file_url=None)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.create",
        entity_type="incapacity_note",
        entity_id=n.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _to_read(n)


@router.post("/{note_id}/attachments", response_model=IncapacityNoteRead)
async def upload_attachment(
    request: Request,
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> IncapacityNoteRead:
    _validate_image_upload(file)
    url = await _save_upload(file)
    body = IncapacityNoteUpdate()
    n = await svc.update_note(db, current, note_id, body, file_url=url)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.upload",
        entity_type="incapacity_note",
        entity_id=note_id,
        details={"file_url": url},
        ip_address=client_ip(request),
    )
    await db.commit()
    return _to_read(n)


@router.get("/{note_id}", response_model=IncapacityNoteRead)
async def get_note(
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> IncapacityNoteRead:
    n = await svc.get_note(db, note_id)
    if not n:
        from app.core.exceptions import not_found

        raise not_found()
    await svc.ensure_employee_scope_for_read(db, current, n)
    return _to_read(n)


@router.get("/{note_id}/comments", response_model=list[IncapacityCommentRead])
async def list_comments(
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> list[IncapacityCommentRead]:
    n = await svc.get_note(db, note_id)
    if not n:
        from app.core.exceptions import not_found

        raise not_found()
    await svc.ensure_employee_scope_for_read(db, current, n)
    return [IncapacityCommentRead.model_validate(c) for c in (n.comments or [])]


@router.post("/{note_id}/comments", response_model=IncapacityCommentRead)
async def add_comment(
    request: Request,
    note_id: int,
    body: IncapacityCommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> IncapacityCommentRead:
    c = await svc.add_comment(db, current, note_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.comment",
        entity_type="incapacity_note",
        entity_id=note_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return IncapacityCommentRead.model_validate(c)


@router.patch("/{note_id}", response_model=IncapacityNoteRead)
async def update_note(
    request: Request,
    note_id: int,
    body: IncapacityNoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> IncapacityNoteRead:
    n = await svc.update_note(db, current, note_id, body, file_url=None)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.update",
        entity_type="incapacity_note",
        entity_id=note_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _to_read(n)


@router.delete("/{note_id}")
async def delete_note(
    request: Request,
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    await svc.delete_note(db, current, note_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.delete",
        entity_type="incapacity_note",
        entity_id=note_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return {"detail": "Operación correcta"}

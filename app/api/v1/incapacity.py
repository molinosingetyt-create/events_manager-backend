import math
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.core.exceptions import bad_request
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import LongAbsenceDocumentKind
from app.models.user import User
from app.api.v1.employees import _employee_read
from app.schemas.common import PaginatedResponse
from app.schemas.employee import EmployeeRead
from app.schemas.incapacity import (
    IncapacityCommentCreate,
    IncapacityCommentRead,
    IncapacityExtensionCreate,
    IncapacityExtensionRead,
    IncapacityHistoryRead,
    IncapacityNoteCreate,
    IncapacityNoteRead,
    IncapacityNoteUpdate,
    LeaderFilterOption,
)
from app.schemas.overtime import UserBriefRead
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import incapacity_catalog_service as catalog_svc
from app.services import incapacity_service as svc
from app.schemas.incapacity_catalog import IncapacityFormOptionsRead

router = APIRouter()
settings = get_settings()


def _user_brief(u) -> UserBriefRead | None:
    if u is None:
        return None
    return UserBriefRead(id=u.id, name=u.name, email=u.email)


def _extension_read(ext) -> IncapacityExtensionRead:
    return IncapacityExtensionRead(
        id=ext.id,
        incapacity_id=ext.incapacity_id,
        start_date=ext.start_date,
        end_date=ext.end_date,
        file_url=ext.file_url,
        note=ext.note,
        created_by=ext.created_by,
        creator=_user_brief(ext.creator),
        created_at=ext.created_at,
        updated_at=ext.updated_at,
    )


def _eps_arl_label(note) -> str:
    e = note.eps_arl
    if not e:
        return ""
    kind_es = "EPS" if e.kind == "eps" else "ARL"
    return f"{kind_es} — {e.name}"


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
    employee_identification = emp.identification_number if emp is not None else ""
    tc = note.temporal_category
    temporal_name = tc.name if tc is not None else ""
    dg = note.diagnosis
    exts = sorted(note.extensions or [], key=lambda x: x.id)
    return IncapacityNoteRead(
        id=note.id,
        employee_id=note.employee_id,
        employee_name=employee_name,
        employee_identification=employee_identification,
        type=note.type,
        temporal_category_id=note.temporal_category_id,
        temporal_category_name=temporal_name,
        eps_arl_id=note.eps_arl_id,
        eps_arl_label=_eps_arl_label(note),
        diagnosis_id=note.diagnosis_id,
        diagnosis_code=dg.code if dg is not None else "",
        diagnosis_name=dg.name if dg is not None else "",
        description=note.description,
        support=note.support,
        start_date=note.start_date,
        end_date=note.end_date,
        long_absence_document_kind=note.long_absence_document_kind,
        file_url=note.file_url,
        long_absence_second_file_url=note.long_absence_second_file_url,
        long_absence_eps_transcribed_text=note.long_absence_eps_transcribed_text,
        created_by=note.created_by,
        creator=_user_brief(note.creator),
        status=note.status,
        created_at=note.created_at,
        updated_at=note.updated_at,
        history=hist,
        extensions=[_extension_read(e) for e in exts],
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


def _is_nonempty_upload(upload: UploadFile | None) -> bool:
    return upload is not None and bool(upload.filename)


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


@router.get("/form-options", response_model=IncapacityFormOptionsRead)
async def form_options(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_any_permission("incapacity.view"))],
) -> IncapacityFormOptionsRead:
    """Listas activas para selectores al crear/editar incapacidad (temporal, EPS/ARL, diagnósticos)."""
    return await catalog_svc.get_form_options(db)


@router.get("/leader-filter-options", response_model=list[LeaderFilterOption])
async def leader_filter_options(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_any_permission("incapacity.view"))],
) -> list[LeaderFilterOption]:
    """Líderes de usuario (activos) para filtrar incapacidades por colaborador asignado."""
    rows = await svc.list_leader_filter_options(db)
    return [LeaderFilterOption(id=i, name=n) for i, n in rows]


@router.get("/assignable-employees", response_model=PaginatedResponse[EmployeeRead])
async def list_assignable_employees(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("incapacity.create"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    search: str | None = Query(None, description="Buscar por nombre o número de identificación"),
) -> PaginatedResponse[EmployeeRead]:
    """Empleados del equipo del líder (sin filtro por área) para el formulario de incapacidades."""
    items, total = await svc.list_assignable_employees(
        db, current, page=page, page_size=page_size, search=search
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.assignable_employees",
        entity_type="employee",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_employee_read(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("", response_model=PaginatedResponse[IncapacityNoteRead])
async def list_notes(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    employee_id: int | None = None,
    type: str | None = Query(None, alias="type_filter"),
    search: str | None = Query(None, description="Buscar por nombre o identificación del empleado"),
    leader_id: int | None = Query(None, description="Filtrar por líder asignado al empleado (id de usuario)"),
) -> PaginatedResponse[IncapacityNoteRead]:
    items, total = await svc.list_notes(
        db,
        current,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        type_filter=type,
        search=search,
        leader_id=leader_id,
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
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("incapacity.create"))],
    file: UploadFile | None = File(None),
    payload: str = Form(..., description="JSON con los campos de IncapacityNoteCreate"),
    file_historia_clinica: UploadFile | None = File(None),
    file_eps: UploadFile | None = File(None),
) -> IncapacityNoteRead:
    body = IncapacityNoteCreate.model_validate_json(payload)
    url: str | None = None
    if _is_nonempty_upload(file):
        assert file is not None
        _validate_image_upload(file)
        url = await _save_upload(file)

    days = svc.inclusive_incapacity_days(body.start_date, body.end_date)
    kind_val = body.long_absence_document_kind.value if body.long_absence_document_kind else None
    second_url: str | None = None

    if days >= 3 and kind_val == LongAbsenceDocumentKind.HISTORIA_CLINICA.value:
        if _is_nonempty_upload(file_eps):
            raise bad_request("Use el archivo «historia clínica» para la imagen adicional, no el campo de EPS.")
        if not _is_nonempty_upload(file_historia_clinica):
            raise bad_request("Adjunte la imagen adicional de historia clínica.")
        assert file_historia_clinica is not None
        _validate_image_upload(file_historia_clinica)
        second_url = await _save_upload(file_historia_clinica)
    elif days >= 3 and kind_val == LongAbsenceDocumentKind.INCAPACIDAD_EPS.value:
        if _is_nonempty_upload(file_historia_clinica):
            raise bad_request("Use el archivo «EPS» para la foto de la incapacidad transcrita, no el de historia clínica.")
        if not _is_nonempty_upload(file_eps):
            raise bad_request("Adjunte la foto obligatoria de la incapacidad transcrita por EPS.")
        assert file_eps is not None
        _validate_image_upload(file_eps)
        second_url = await _save_upload(file_eps)
    elif _is_nonempty_upload(file_historia_clinica) or _is_nonempty_upload(file_eps):
        raise bad_request("No adjunte soporte adicional si la incapacidad es de menos de 3 días.")

    n = await svc.create_note(
        db,
        current,
        body,
        file_url=url,
        long_absence_second_file_url=second_url,
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.create",
        entity_type="incapacity_note",
        entity_id=n.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["incapacity", "notifications"])
    return _to_read(n)


@router.post("/{note_id}/attachments", response_model=IncapacityNoteRead)
async def upload_attachment(
    request: Request,
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("incapacity.edit"))],
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
    await broadcast_data_changed(["incapacity"])
    return _to_read(n)


@router.post("/{note_id}/extensions", response_model=IncapacityNoteRead)
async def add_incapacity_extension(
    request: Request,
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("incapacity.extension"))],
    file: UploadFile = File(...),
    payload: str = Form(..., description="JSON: IncapacityExtensionCreate"),
) -> IncapacityNoteRead:
    body = IncapacityExtensionCreate.model_validate_json(payload)
    if body.end_date < body.start_date:
        raise bad_request("La fecha fin no puede ser anterior a la fecha de inicio.")
    _validate_image_upload(file)
    url = await _save_upload(file)
    await svc.create_extension(
        db,
        current,
        note_id,
        start_date=body.start_date,
        end_date=body.end_date,
        file_url=url,
        note_text=body.note,
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="incapacity.extension",
        entity_type="incapacity_note",
        entity_id=note_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["incapacity"])
    n = await svc.get_note(db, note_id)
    if not n:
        from app.core.exceptions import not_found

        raise not_found()
    await svc.ensure_employee_scope_for_read(db, current, n)
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
    await broadcast_data_changed(["incapacity"])
    return IncapacityCommentRead.model_validate(c)


@router.patch("/{note_id}", response_model=IncapacityNoteRead)
async def update_note(
    request: Request,
    note_id: int,
    body: IncapacityNoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("incapacity.edit"))],
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
    await broadcast_data_changed(["incapacity"])
    return _to_read(n)


@router.delete("/{note_id}")
async def delete_note(
    request: Request,
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("incapacity.delete"))],
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
    await broadcast_data_changed(["incapacity"])
    return {"detail": "Operación correcta"}

"""Documentos digitalizados del expediente HR."""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.file_upload import save_upload_file, validate_profile_document_upload
from app.core.exceptions import not_found
from app.models.employee_document import EmployeeDocument
from app.models.user import User
from app.schemas.employee_profile import (
    DOCUMENT_KIND_LABELS,
    EmployeeDocumentCreate,
    EmployeeDocumentRead,
    EmployeeDocumentUpdate,
)
from app.services.employee_profile_mappers import document_read
from app.services.employee_profile_service import user_can_edit_profile, user_can_view_full_profile
from app.services.employee_service import ensure_employee_access, get_employee

_VALID_STATUS = frozenset({"vigente", "vencido", "pendiente"})


async def list_documents(
    db: AsyncSession,
    actor: User,
    employee_id: int,
) -> list[EmployeeDocumentRead]:
    if not await user_can_view_full_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para ver documentos del expediente")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    r = await db.execute(
        select(EmployeeDocument)
        .options(selectinload(EmployeeDocument.uploaded_by))
        .where(EmployeeDocument.employee_id == employee_id)
        .order_by(EmployeeDocument.created_at.desc())
    )
    return [document_read(row) for row in r.scalars().all()]


async def create_document(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    meta: EmployeeDocumentCreate,
    upload: UploadFile,
) -> EmployeeDocumentRead:
    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para cargar documentos")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    if meta.document_kind not in DOCUMENT_KIND_LABELS:
        from app.core.exceptions import bad_request

        raise bad_request("Tipo de documento no válido")
    if meta.status not in _VALID_STATUS:
        from app.core.exceptions import bad_request

        raise bad_request("Estado no válido")
    validate_profile_document_upload(upload)
    file_url, content_type, size = await save_upload_file(upload)
    display = (meta.display_name or "").strip() or DOCUMENT_KIND_LABELS[meta.document_kind]
    row = EmployeeDocument(
        employee_id=employee_id,
        document_kind=meta.document_kind,
        display_name=display,
        file_url=file_url,
        content_type=content_type,
        file_size=size,
        status=meta.status,
        expires_at=meta.expires_at,
        uploaded_by_id=actor.id,
    )
    db.add(row)
    await db.commit()
    r = await db.execute(
        select(EmployeeDocument)
        .options(selectinload(EmployeeDocument.uploaded_by))
        .where(EmployeeDocument.id == row.id)
    )
    saved = r.scalar_one()
    return document_read(saved)


async def update_document(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    document_id: int,
    body: EmployeeDocumentUpdate,
) -> EmployeeDocumentRead:
    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para editar documentos")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    r = await db.execute(
        select(EmployeeDocument)
        .options(selectinload(EmployeeDocument.uploaded_by))
        .where(
            EmployeeDocument.id == document_id,
            EmployeeDocument.employee_id == employee_id,
        )
    )
    row = r.scalar_one_or_none()
    if not row:
        raise not_found("Documento no encontrado")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in _VALID_STATUS:
        from app.core.exceptions import bad_request

        raise bad_request("Estado no válido")
    for key, val in data.items():
        setattr(row, key, val)
    await db.commit()
    await db.refresh(row)
    return document_read(row)


async def delete_document(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    document_id: int,
) -> None:
    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para eliminar documentos")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    r = await db.execute(
        select(EmployeeDocument.id).where(
            EmployeeDocument.id == document_id,
            EmployeeDocument.employee_id == employee_id,
        )
    )
    if r.scalar_one_or_none() is None:
        raise not_found("Documento no encontrado")
    await db.execute(
        delete(EmployeeDocument).where(
            EmployeeDocument.id == document_id,
            EmployeeDocument.employee_id == employee_id,
        )
    )
    await db.commit()

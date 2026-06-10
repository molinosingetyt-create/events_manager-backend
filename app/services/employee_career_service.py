"""Certificados adjuntos en formación y capacitaciones."""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_upload import save_upload_file, validate_profile_document_upload
from app.core.exceptions import not_found
from app.models.employee_career import EmployeeEducation, EmployeeTraining
from app.models.user import User
from app.schemas.employee_profile import EmployeeEducationRead, EmployeeTrainingRead
from app.services.employee_profile_mappers import education_read, training_read
from app.services.employee_profile_service import user_can_edit_profile
from app.services.employee_service import ensure_employee_access, get_employee


async def upload_education_certificate(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    record_id: int,
    upload: UploadFile,
) -> EmployeeEducationRead:
    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para editar el expediente")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    r = await db.execute(
        select(EmployeeEducation).where(
            EmployeeEducation.id == record_id,
            EmployeeEducation.employee_id == employee_id,
        )
    )
    row = r.scalar_one_or_none()
    if not row:
        raise not_found("Registro académico no encontrado")
    validate_profile_document_upload(upload)
    url, _, _ = await save_upload_file(upload)
    row.certificate_url = url
    await db.commit()
    await db.refresh(row)
    return education_read(row)


async def upload_training_certificate(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    record_id: int,
    upload: UploadFile,
) -> EmployeeTrainingRead:
    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para editar el expediente")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    r = await db.execute(
        select(EmployeeTraining).where(
            EmployeeTraining.id == record_id,
            EmployeeTraining.employee_id == employee_id,
        )
    )
    row = r.scalar_one_or_none()
    if not row:
        raise not_found("Registro de capacitación no encontrado")
    validate_profile_document_upload(upload)
    url, _, _ = await save_upload_file(upload)
    row.certificate_url = url
    await db.commit()
    await db.refresh(row)
    return training_read(row)

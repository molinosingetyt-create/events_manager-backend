from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.date_range import calc_inclusive_days
from app.core.exceptions import bad_request, forbidden, not_found
from app.models.absenteeism import AbsenteeismRecord
from app.models.employee import Employee
from app.models.enums import EntityStatus, Role
from app.models.user import User
from app.schemas.absenteeism import AbsenteeismRecordCreate, AbsenteeismRecordUpdate
from app.services.employee_service import acts_as_team_leader, ensure_employee_access
from app.services.rbac_service import behavior_key

_LOAD = (
    selectinload(AbsenteeismRecord.employee),
    selectinload(AbsenteeismRecord.creator),
)


async def list_records(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    employee_id: int | None = None,
    classification: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[AbsenteeismRecord], int]:
    q = select(AbsenteeismRecord)
    count_q = select(func.count()).select_from(AbsenteeismRecord)
    if acts_as_team_leader(actor) or employee_id is not None:
        q = q.join(Employee, AbsenteeismRecord.employee_id == Employee.id)
        count_q = count_q.join(Employee, AbsenteeismRecord.employee_id == Employee.id)
    if acts_as_team_leader(actor):
        q = q.where(Employee.leader_id == actor.id)
        count_q = count_q.where(Employee.leader_id == actor.id)
    if employee_id is not None:
        q = q.where(AbsenteeismRecord.employee_id == employee_id)
        count_q = count_q.where(AbsenteeismRecord.employee_id == employee_id)
    if classification:
        q = q.where(AbsenteeismRecord.classification == classification)
        count_q = count_q.where(AbsenteeismRecord.classification == classification)
    if date_from is not None:
        q = q.where(AbsenteeismRecord.end_date >= date_from)
        count_q = count_q.where(AbsenteeismRecord.end_date >= date_from)
    if date_to is not None:
        q = q.where(AbsenteeismRecord.start_date <= date_to)
        count_q = count_q.where(AbsenteeismRecord.start_date <= date_to)
    total = (await db.execute(count_q)).scalar_one()
    q = (
        q.order_by(AbsenteeismRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(*_LOAD)
    )
    return list((await db.execute(q)).scalars().all()), total


async def get_record(db: AsyncSession, record_id: int) -> AbsenteeismRecord | None:
    r = await db.execute(
        select(AbsenteeismRecord).options(*_LOAD).where(AbsenteeismRecord.id == record_id)
    )
    return r.scalar_one_or_none()


async def create_record(
    db: AsyncSession, actor: User, data: AbsenteeismRecordCreate
) -> AbsenteeismRecord:
    if behavior_key(actor) not in (
        Role.LEADER.value,
        Role.ADMIN.value,
        Role.HR.value,
        Role.MANAGEMENT.value,
    ):
        raise forbidden("No tiene permiso para registrar ausentismo")
    er = await db.execute(select(Employee).where(Employee.id == data.employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise bad_request("Empleado no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, emp)
    days = calc_inclusive_days(data.start_date, data.end_date)
    row = AbsenteeismRecord(
        employee_id=data.employee_id,
        created_by=actor.id,
        classification=data.classification.value,
        start_date=data.start_date,
        end_date=data.end_date,
        days=days,
        justification=data.justification,
        status=data.status.value,
    )
    db.add(row)
    await db.commit()
    saved = await get_record(db, row.id)
    assert saved is not None
    return saved


async def update_record(
    db: AsyncSession, actor: User, record_id: int, data: AbsenteeismRecordUpdate
) -> AbsenteeismRecord:
    row = await get_record(db, record_id)
    if not row:
        raise not_found("Registro de ausentismo no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, row.employee)
    elif behavior_key(actor) not in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        raise forbidden("No puede editar este registro")
    if data.classification is not None:
        row.classification = data.classification.value
    if data.start_date is not None:
        row.start_date = data.start_date
    if data.end_date is not None:
        row.end_date = data.end_date
    if data.justification is not None:
        row.justification = data.justification
    if data.status is not None:
        row.status = data.status.value
    if data.start_date is not None or data.end_date is not None:
        row.days = calc_inclusive_days(row.start_date, row.end_date)
    await db.commit()
    saved = await get_record(db, record_id)
    assert saved is not None
    return saved


async def delete_record(db: AsyncSession, actor: User, record_id: int) -> None:
    if behavior_key(actor) not in (Role.ADMIN.value, Role.HR.value):
        raise forbidden("No tiene permiso para eliminar")
    row = await get_record(db, record_id)
    if not row:
        raise not_found("Registro de ausentismo no encontrado")
    await db.execute(delete(AbsenteeismRecord).where(AbsenteeismRecord.id == record_id))
    await db.commit()

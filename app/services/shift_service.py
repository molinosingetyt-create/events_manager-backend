from datetime import date, time

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.core.overtime_time import calc_overtime_hours
from app.models.employee import Employee
from app.models.enums import Role
from app.models.shift import ShiftSchedule
from app.models.user import User
from app.schemas.shift import ShiftScheduleCreate, ShiftScheduleUpdate
from app.services.employee_service import acts_as_team_leader, ensure_employee_access
from app.services.rbac_service import behavior_key

_LOAD = (
    selectinload(ShiftSchedule.employee),
    selectinload(ShiftSchedule.creator),
)


def _validate_shift_times(start: time, end: time) -> None:
    calc_overtime_hours(start, end)


async def list_shifts(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    employee_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[ShiftSchedule], int]:
    q = select(ShiftSchedule)
    count_q = select(func.count()).select_from(ShiftSchedule)
    if acts_as_team_leader(actor) or employee_id is not None:
        q = q.join(Employee, ShiftSchedule.employee_id == Employee.id)
        count_q = count_q.join(Employee, ShiftSchedule.employee_id == Employee.id)
    if acts_as_team_leader(actor):
        q = q.where(Employee.leader_id == actor.id)
        count_q = count_q.where(Employee.leader_id == actor.id)
    if employee_id is not None:
        q = q.where(ShiftSchedule.employee_id == employee_id)
        count_q = count_q.where(ShiftSchedule.employee_id == employee_id)
    if date_from is not None:
        q = q.where(ShiftSchedule.shift_date >= date_from)
        count_q = count_q.where(ShiftSchedule.shift_date >= date_from)
    if date_to is not None:
        q = q.where(ShiftSchedule.shift_date <= date_to)
        count_q = count_q.where(ShiftSchedule.shift_date <= date_to)
    total = (await db.execute(count_q)).scalar_one()
    q = (
        q.order_by(ShiftSchedule.shift_date.desc(), ShiftSchedule.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(*_LOAD)
    )
    return list((await db.execute(q)).scalars().all()), total


async def get_shift(db: AsyncSession, shift_id: int) -> ShiftSchedule | None:
    r = await db.execute(
        select(ShiftSchedule).options(*_LOAD).where(ShiftSchedule.id == shift_id)
    )
    return r.scalar_one_or_none()


async def create_shift(db: AsyncSession, actor: User, data: ShiftScheduleCreate) -> ShiftSchedule:
    if behavior_key(actor) not in (
        Role.LEADER.value,
        Role.ADMIN.value,
        Role.HR.value,
        Role.MANAGEMENT.value,
    ):
        raise forbidden("No tiene permiso para programar turnos")
    er = await db.execute(select(Employee).where(Employee.id == data.employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise bad_request("Empleado no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, emp)
    _validate_shift_times(data.start_time, data.end_time)
    row = ShiftSchedule(
        employee_id=data.employee_id,
        created_by=actor.id,
        shift_date=data.shift_date,
        start_time=data.start_time,
        end_time=data.end_time,
        notes=data.notes,
        status=data.status.value,
    )
    db.add(row)
    await db.commit()
    saved = await get_shift(db, row.id)
    assert saved is not None
    return saved


async def update_shift(
    db: AsyncSession, actor: User, shift_id: int, data: ShiftScheduleUpdate
) -> ShiftSchedule:
    row = await get_shift(db, shift_id)
    if not row:
        raise not_found("Turno no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, row.employee)
    elif behavior_key(actor) not in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        raise forbidden("No puede editar este turno")
    if data.shift_date is not None:
        row.shift_date = data.shift_date
    if data.start_time is not None:
        row.start_time = data.start_time
    if data.end_time is not None:
        row.end_time = data.end_time
    if data.notes is not None:
        row.notes = data.notes
    if data.status is not None:
        row.status = data.status.value
    _validate_shift_times(row.start_time, row.end_time)
    await db.commit()
    saved = await get_shift(db, shift_id)
    assert saved is not None
    return saved


async def delete_shift(db: AsyncSession, actor: User, shift_id: int) -> None:
    if behavior_key(actor) not in (Role.ADMIN.value, Role.HR.value):
        raise forbidden("No tiene permiso para eliminar")
    row = await get_shift(db, shift_id)
    if not row:
        raise not_found("Turno no encontrado")
    await db.execute(delete(ShiftSchedule).where(ShiftSchedule.id == shift_id))
    await db.commit()

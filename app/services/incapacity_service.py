import json
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.employee import Employee
from app.models.enums import EntityStatus, IncapacityHistoryAction, Role
from app.models.incapacity import IncapacityComment, IncapacityNote, IncapacityNoteHistory
from app.models.user import User
from app.schemas.incapacity import IncapacityCommentCreate, IncapacityNoteCreate, IncapacityNoteUpdate

_INC_BASE = (
    selectinload(IncapacityNote.employee),
    selectinload(IncapacityNote.creator),
    selectinload(IncapacityNote.history_entries).selectinload(IncapacityNoteHistory.user),
)
_INC_FULL = _INC_BASE + (
    selectinload(IncapacityNote.comments).selectinload(IncapacityComment.user),
)


def _snapshot(note: IncapacityNote) -> str:
    return json.dumps(
        {
            "employee_id": note.employee_id,
            "type": note.type,
            "description": note.description,
            "support": note.support,
            "start_date": str(note.start_date),
            "end_date": str(note.end_date) if note.end_date else None,
            "status": note.status,
            "file_url": note.file_url,
        }
    )


async def _add_history(
    db: AsyncSession,
    incapacity_id: int,
    action: str,
    user_id: int | None,
    comment: str | None,
    snapshot: str | None,
) -> None:
    h = IncapacityNoteHistory(
        incapacity_id=incapacity_id,
        action=action,
        user_id=user_id,
        comment=comment,
        snapshot=snapshot,
        created_at=datetime.now(timezone.utc),
    )
    db.add(h)


async def get_note(db: AsyncSession, note_id: int) -> IncapacityNote | None:
    r = await db.execute(
        select(IncapacityNote)
        .options(*_INC_FULL)
        .where(IncapacityNote.id == note_id)
    )
    return r.scalar_one_or_none()


async def list_notes(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    employee_id: int | None = None,
    type_filter: str | None = None,
) -> tuple[list[IncapacityNote], int]:
    q = select(IncapacityNote)
    count_q = select(func.count()).select_from(IncapacityNote)

    if actor.role == Role.LEADER.value:
        sub = select(Employee.id).where(Employee.area_id == actor.area_id)
        q = q.where(IncapacityNote.employee_id.in_(sub))
        count_q = count_q.where(IncapacityNote.employee_id.in_(sub))

    if employee_id is not None:
        q = q.where(IncapacityNote.employee_id == employee_id)
        count_q = count_q.where(IncapacityNote.employee_id == employee_id)
    if type_filter:
        q = q.where(IncapacityNote.type == type_filter)
        count_q = count_q.where(IncapacityNote.type == type_filter)

    total = (await db.execute(count_q)).scalar_one()
    q = (
        q.order_by(IncapacityNote.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(*_INC_BASE)
    )
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def ensure_employee_scope(db: AsyncSession, actor: User, employee_id: int) -> Employee:
    er = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise bad_request("Empleado no encontrado")
    if actor.role == Role.LEADER.value and emp.area_id != actor.area_id:
        raise forbidden("El empleado no está en su área")
    return emp


async def create_note(
    db: AsyncSession,
    actor: User,
    data: IncapacityNoteCreate,
    file_url: str | None,
) -> IncapacityNote:
    if actor.role == Role.LEADER.value:
        await ensure_employee_scope(db, actor, data.employee_id)
    elif actor.role in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        er = await db.execute(select(Employee).where(Employee.id == data.employee_id))
        if not er.scalar_one_or_none():
            raise bad_request("Empleado no encontrado")
    else:
        raise forbidden("No tiene permiso para crear este registro")

    # Solo gerencia o administración pueden dejar registros ya aprobados/rechazados; el resto queda pendiente.
    if actor.role in (Role.MANAGEMENT.value, Role.ADMIN.value):
        status_val = data.status.value
    else:
        status_val = EntityStatus.PENDING.value

    note = IncapacityNote(
        employee_id=data.employee_id,
        type=data.type.value,
        description=data.description,
        support=(data.support.strip() if data.support and data.support.strip() else None),
        start_date=data.start_date,
        end_date=data.end_date,
        file_url=file_url,
        created_by=actor.id,
        status=status_val,
    )
    db.add(note)
    await db.flush()
    await _add_history(
        db,
        note.id,
        IncapacityHistoryAction.CREATED.value,
        actor.id,
        None,
        _snapshot(note),
    )
    await db.commit()
    r2 = await db.execute(select(IncapacityNote).options(*_INC_FULL).where(IncapacityNote.id == note.id))
    return r2.scalar_one()


async def update_note(
    db: AsyncSession, actor: User, note_id: int, data: IncapacityNoteUpdate, file_url: str | None
) -> IncapacityNote:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")

    emp = await ensure_employee_scope_for_read(db, actor, note)

    if not can_modify_note(actor, note, emp):
        raise forbidden("No puede modificar este registro")

    old_status = note.status

    if data.type is not None:
        note.type = data.type.value
    if data.description is not None:
        note.description = data.description
    if data.support is not None:
        note.support = data.support.strip() or None
    if data.start_date is not None:
        note.start_date = data.start_date
    if data.end_date is not None:
        note.end_date = data.end_date
    if data.status is not None:
        new_s = data.status.value
        if new_s in (EntityStatus.APPROVED.value, EntityStatus.REJECTED.value):
            if actor.role not in (Role.MANAGEMENT.value, Role.ADMIN.value):
                raise forbidden("Solo gerencia o administración pueden aprobar o rechazar")
            if note.status != EntityStatus.PENDING.value:
                raise bad_request("Solo se pueden aprobar o rechazar registros pendientes")
        note.status = new_s
    if file_url is not None:
        note.file_url = file_url

    decision = (
        data.status is not None
        and old_status == EntityStatus.PENDING.value
        and note.status in (EntityStatus.APPROVED.value, EntityStatus.REJECTED.value)
    )
    if decision:
        action = (
            IncapacityHistoryAction.APPROVED.value
            if note.status == EntityStatus.APPROVED.value
            else IncapacityHistoryAction.REJECTED.value
        )
        await _add_history(db, note_id, action, actor.id, None, _snapshot(note))
    elif (
        file_url is not None
        or data.type is not None
        or data.description is not None
        or data.support is not None
        or data.start_date is not None
        or data.end_date is not None
        or (data.status is not None and not decision)
    ):
        comment = "Se adjuntó un archivo" if file_url is not None and not any(
            [
                data.type is not None,
                data.description is not None,
                data.support is not None,
                data.start_date is not None,
                data.end_date is not None,
                data.status is not None,
            ]
        ) else None
        await _add_history(
            db,
            note_id,
            IncapacityHistoryAction.UPDATED.value,
            actor.id,
            comment or "Registro actualizado",
            _snapshot(note),
        )

    await db.commit()
    r2 = await db.execute(select(IncapacityNote).options(*_INC_FULL).where(IncapacityNote.id == note_id))
    return r2.scalar_one()


async def ensure_employee_scope_for_read(
    db: AsyncSession, actor: User, note: IncapacityNote
) -> Employee:
    er = await db.execute(select(Employee).where(Employee.id == note.employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise not_found("Empleado no encontrado")
    if actor.role == Role.LEADER.value and emp.area_id != actor.area_id:
        raise forbidden("No puede acceder a este registro")
    return emp


def can_modify_note(actor: User, note: IncapacityNote, emp: Employee) -> bool:
    if actor.role in (Role.ADMIN.value, Role.HR.value):
        return True
    if actor.role == Role.LEADER.value:
        return emp.area_id == actor.area_id and note.created_by == actor.id
    if actor.role == Role.MANAGEMENT.value:
        return True
    return False


async def add_comment(
    db: AsyncSession, actor: User, note_id: int, data: IncapacityCommentCreate
) -> IncapacityComment:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")
    await ensure_employee_scope_for_read(db, actor, note)

    c = IncapacityComment(
        incapacity_id=note_id,
        user_id=actor.id,
        comment=data.comment,
        created_at=datetime.now(timezone.utc),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def delete_note(db: AsyncSession, actor: User, note_id: int) -> None:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")
    emp = await ensure_employee_scope_for_read(db, actor, note)
    if not can_modify_note(actor, note, emp):
        raise forbidden("No puede eliminar este registro")
    await db.execute(delete(IncapacityNote).where(IncapacityNote.id == note_id))
    await db.commit()

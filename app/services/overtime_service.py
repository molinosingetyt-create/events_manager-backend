import json
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.employee import Employee
from app.models.enums import EntityStatus, OvertimeHistoryAction, Role
from app.models.overtime import OvertimeRequest, OvertimeRequestHistory
from app.models.user import User

_OT_LOAD = (
    selectinload(OvertimeRequest.employee),
    selectinload(OvertimeRequest.requester),
    selectinload(OvertimeRequest.approver),
    selectinload(OvertimeRequest.history_entries).selectinload(OvertimeRequestHistory.user),
)
from app.core.overtime_time import calc_overtime_hours
from app.schemas.overtime import OvertimeApproveReject, OvertimeRequestCreate, OvertimeRequestUpdate
from app.services import notification_service as notif_svc
from app.services.employee_service import (
    acts_as_team_leader,
    ensure_employee_access,
    list_assignable_employees_for_actor,
)
from app.services.rbac_service import behavior_key


def _snapshot(req: OvertimeRequest) -> str:
    payload: dict[str, str | int] = {
        "employee_id": req.employee_id,
        "date": str(req.date),
        "hours": str(req.hours),
        "status": req.status,
    }
    if req.start_time is not None:
        payload["start_time"] = req.start_time.strftime("%H:%M")
    if req.end_time is not None:
        payload["end_time"] = req.end_time.strftime("%H:%M")
    return json.dumps(payload)


async def _add_history(
    db: AsyncSession,
    request_id: int,
    action: str,
    user_id: int | None,
    comment: str | None,
    snapshot: str | None,
) -> None:
    h = OvertimeRequestHistory(
        request_id=request_id,
        action=action,
        user_id=user_id,
        comment=comment,
        snapshot=snapshot,
        created_at=datetime.now(timezone.utc),
    )
    db.add(h)


async def list_assignable_employees(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[list[Employee], int]:
    return await list_assignable_employees_for_actor(
        db, actor, page=page, page_size=page_size, search=search
    )


async def ensure_can_view(db: AsyncSession, actor: User, req: OvertimeRequest) -> None:
    if acts_as_team_leader(actor):
        er = await db.execute(select(Employee).where(Employee.id == req.employee_id))
        emp = er.scalar_one_or_none()
        if not emp:
            raise forbidden("No puede acceder a esta solicitud")
        ensure_employee_access(actor, emp)


async def get_request(db: AsyncSession, request_id: int) -> OvertimeRequest | None:
    r = await db.execute(
        select(OvertimeRequest).options(*_OT_LOAD).where(OvertimeRequest.id == request_id)
    )
    return r.scalar_one_or_none()


async def list_requests(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    employee_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[OvertimeRequest], int]:
    q = select(OvertimeRequest)
    count_q = select(func.count()).select_from(OvertimeRequest)

    if acts_as_team_leader(actor):
        sub = select(Employee.id).where(Employee.leader_id == actor.id)
        q = q.where(OvertimeRequest.employee_id.in_(sub))
        count_q = count_q.where(OvertimeRequest.employee_id.in_(sub))

    if status:
        q = q.where(OvertimeRequest.status == status)
        count_q = count_q.where(OvertimeRequest.status == status)
    if employee_id is not None:
        q = q.where(OvertimeRequest.employee_id == employee_id)
        count_q = count_q.where(OvertimeRequest.employee_id == employee_id)
    if date_from is not None:
        q = q.where(OvertimeRequest.date >= date_from)
        count_q = count_q.where(OvertimeRequest.date >= date_from)
    if date_to is not None:
        q = q.where(OvertimeRequest.date <= date_to)
        count_q = count_q.where(OvertimeRequest.date <= date_to)

    total = (await db.execute(count_q)).scalar_one()
    q = (
        q.order_by(OvertimeRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(*_OT_LOAD)
    )
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def create_requests(
    db: AsyncSession, actor: User, data: OvertimeRequestCreate
) -> tuple[list[OvertimeRequest], Decimal, Decimal]:
    allowed_create = (
        Role.LEADER.value,
        Role.ADMIN.value,
        Role.HR.value,
        Role.MANAGEMENT.value,
    )
    if behavior_key(actor) not in allowed_create:
        raise forbidden("No tiene permiso para crear solicitudes de horas extra")

    er = await db.execute(select(Employee).where(Employee.id == data.employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise bad_request("Empleado no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, emp)

    hours_per_day = calc_overtime_hours(data.start_time, data.end_time)
    sorted_dates = sorted(data.dates)
    created_ids: list[int] = []

    for work_date in sorted_dates:
        req = OvertimeRequest(
            employee_id=data.employee_id,
            requested_by=actor.id,
            date=work_date,
            hours=hours_per_day,
            start_time=data.start_time,
            end_time=data.end_time,
            justification=data.justification,
            status=EntityStatus.PENDING.value,
        )
        db.add(req)
        await db.flush()
        created_ids.append(req.id)
        await _add_history(
            db,
            req.id,
            OvertimeHistoryAction.CREATED.value,
            actor.id,
            None,
            _snapshot(req),
        )
        en = await db.execute(select(Employee.name).where(Employee.id == req.employee_id))
        emp_name = en.scalar_one()
        await notif_svc.notify_admins_new_pending_ot(
            db,
            request_id=req.id,
            employee_name=emp_name,
            request_date=str(req.date),
            hours=str(req.hours),
            exclude_user_id=actor.id
            if behavior_key(actor) in (Role.ADMIN.value, Role.MANAGEMENT.value)
            else None,
        )

    await db.commit()
    total_hours = (hours_per_day * len(sorted_dates)).quantize(Decimal("0.01"))
    r2 = await db.execute(
        select(OvertimeRequest).options(*_OT_LOAD).where(OvertimeRequest.id.in_(created_ids))
    )
    items = list(r2.scalars().all())
    items.sort(key=lambda x: (x.date, x.id))
    return items, hours_per_day, total_hours


async def update_request(
    db: AsyncSession, actor: User, request_id: int, data: OvertimeRequestUpdate
) -> OvertimeRequest:
    req = await get_request(db, request_id)
    if not req:
        raise not_found("Solicitud de horas extra no encontrada")
    if req.status != EntityStatus.PENDING.value:
        raise bad_request("Solo se pueden editar solicitudes pendientes")

    if acts_as_team_leader(actor):
        if req.requested_by != actor.id:
            raise forbidden("No puede editar esta solicitud")
        er = await db.execute(select(Employee).where(Employee.id == req.employee_id))
        emp = er.scalar_one_or_none()
        if not emp:
            raise forbidden("Solicitud no válida")
        ensure_employee_access(actor, emp)
    elif behavior_key(actor) in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        pass
    else:
        raise forbidden("No puede editar esta solicitud")

    if data.date is not None:
        req.date = data.date
    if data.start_time is not None:
        req.start_time = data.start_time
    if data.end_time is not None:
        req.end_time = data.end_time
    if data.justification is not None:
        req.justification = data.justification

    if req.start_time is not None and req.end_time is not None:
        req.hours = calc_overtime_hours(req.start_time, req.end_time)

    await _add_history(
        db,
        req.id,
        OvertimeHistoryAction.UPDATED.value,
        actor.id,
        "Solicitud actualizada",
        _snapshot(req),
    )
    await db.commit()
    r2 = await db.execute(select(OvertimeRequest).options(*_OT_LOAD).where(OvertimeRequest.id == req.id))
    return r2.scalar_one()


async def approve_or_reject(
    db: AsyncSession, actor: User, request_id: int, body: OvertimeApproveReject
) -> OvertimeRequest:
    if behavior_key(actor) not in (Role.MANAGEMENT.value, Role.ADMIN.value):
        raise forbidden("Solo gerencia o administración pueden aprobar o rechazar solicitudes de horas extra")

    req = await get_request(db, request_id)
    if not req:
        raise not_found("Solicitud de horas extra no encontrada")
    if req.status != EntityStatus.PENDING.value:
        raise bad_request("La solicitud no está pendiente")

    if body.approved:
        req.status = EntityStatus.APPROVED.value
        action = OvertimeHistoryAction.APPROVED.value
    else:
        req.status = EntityStatus.REJECTED.value
        action = OvertimeHistoryAction.REJECTED.value

    req.approved_by = actor.id
    req.approval_comment = body.approval_comment

    await _add_history(
        db,
        req.id,
        action,
        actor.id,
        body.approval_comment,
        _snapshot(req),
    )
    await notif_svc.delete_pending_ot_for_request(db, req.id)
    await notif_svc.notify_requester_decision(db, req, approved=body.approved)
    await db.commit()
    r2 = await db.execute(select(OvertimeRequest).options(*_OT_LOAD).where(OvertimeRequest.id == req.id))
    return r2.scalar_one()


async def delete_request(db: AsyncSession, actor: User, request_id: int) -> None:
    req = await get_request(db, request_id)
    if not req:
        raise not_found("Solicitud de horas extra no encontrada")
    if behavior_key(actor) not in (Role.ADMIN.value, Role.HR.value):
        raise forbidden("No tiene permiso para eliminar")
    await db.execute(delete(OvertimeRequest).where(OvertimeRequest.id == request_id))
    await db.commit()

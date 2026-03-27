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
from app.schemas.overtime import OvertimeApproveReject, OvertimeRequestCreate, OvertimeRequestUpdate
from app.services import notification_service as notif_svc


def _snapshot(req: OvertimeRequest) -> str:
    return json.dumps(
        {
            "employee_id": req.employee_id,
            "date": str(req.date),
            "hours": str(req.hours),
            "status": req.status,
        }
    )


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


async def ensure_can_view(db: AsyncSession, actor: User, req: OvertimeRequest) -> None:
    if actor.role == Role.LEADER.value:
        er = await db.execute(select(Employee).where(Employee.id == req.employee_id))
        emp = er.scalar_one_or_none()
        if not emp or emp.area_id != actor.area_id:
            raise forbidden("No puede acceder a esta solicitud")


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

    if actor.role == Role.LEADER.value:
        sub = select(Employee.id).where(Employee.area_id == actor.area_id)
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


async def create_request(db: AsyncSession, actor: User, data: OvertimeRequestCreate) -> OvertimeRequest:
    allowed_create = (
        Role.LEADER.value,
        Role.ADMIN.value,
        Role.HR.value,
        Role.MANAGEMENT.value,
    )
    if actor.role not in allowed_create:
        raise forbidden("No tiene permiso para crear solicitudes de horas extra")

    er = await db.execute(select(Employee).where(Employee.id == data.employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise bad_request("Empleado no encontrado")
    if actor.role == Role.LEADER.value and emp.area_id != actor.area_id:
        raise forbidden("El empleado debe pertenecer a su área")

    req = OvertimeRequest(
        employee_id=data.employee_id,
        requested_by=actor.id,
        date=data.date,
        hours=data.hours,
        justification=data.justification,
        status=EntityStatus.PENDING.value,
    )
    db.add(req)
    await db.flush()
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
        if actor.role in (Role.ADMIN.value, Role.MANAGEMENT.value)
        else None,
    )
    await db.commit()
    await db.refresh(req)
    r2 = await db.execute(select(OvertimeRequest).options(*_OT_LOAD).where(OvertimeRequest.id == req.id))
    return r2.scalar_one()


async def update_request(
    db: AsyncSession, actor: User, request_id: int, data: OvertimeRequestUpdate
) -> OvertimeRequest:
    req = await get_request(db, request_id)
    if not req:
        raise not_found("Solicitud de horas extra no encontrada")
    if req.status != EntityStatus.PENDING.value:
        raise bad_request("Solo se pueden editar solicitudes pendientes")

    if actor.role == Role.LEADER.value:
        if req.requested_by != actor.id:
            raise forbidden("No puede editar esta solicitud")
        er = await db.execute(select(Employee).where(Employee.id == req.employee_id))
        emp = er.scalar_one_or_none()
        if not emp or emp.area_id != actor.area_id:
            raise forbidden("Solicitud no válida")
    elif actor.role in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        pass
    else:
        raise forbidden("No puede editar esta solicitud")

    if data.date is not None:
        req.date = data.date
    if data.hours is not None:
        req.hours = data.hours
    if data.justification is not None:
        req.justification = data.justification

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
    if actor.role not in (Role.MANAGEMENT.value, Role.ADMIN.value):
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
    if actor.role not in (Role.ADMIN.value, Role.HR.value):
        raise forbidden("No tiene permiso para eliminar")
    await db.execute(delete(OvertimeRequest).where(OvertimeRequest.id == request_id))
    await db.commit()

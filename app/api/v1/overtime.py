import math
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.api.v1.employees import _employee_read
from app.schemas.common import PaginatedResponse
from app.schemas.employee import EmployeeRead
from app.core.overtime_time import format_time_range_label
from app.schemas.overtime import (
    OvertimeApproveReject,
    OvertimeBatchCreateRead,
    OvertimeHistoryRead,
    OvertimeRequestCreate,
    OvertimeRequestRead,
    OvertimeRequestUpdate,
    UserBriefRead,
)
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import overtime_service as svc

router = APIRouter()


def _user_brief(u) -> UserBriefRead | None:
    if u is None:
        return None
    return UserBriefRead(id=u.id, name=u.name, email=u.email)


def _to_read(req) -> OvertimeRequestRead:
    hist_sorted = sorted(req.history_entries or [], key=lambda h: h.created_at)
    hist = [
        OvertimeHistoryRead(
            id=h.id,
            request_id=h.request_id,
            action=h.action,
            user_id=h.user_id,
            user=_user_brief(h.user),
            comment=h.comment,
            snapshot=h.snapshot,
            created_at=h.created_at,
        )
        for h in hist_sorted
    ]
    requester = req.requester
    requester_read = (
        UserBriefRead(id=requester.id, name=requester.name, email=requester.email)
        if requester is not None
        else UserBriefRead(id=req.requested_by, name="—", email="")
    )
    employee_name = req.employee.name if req.employee is not None else ""
    return OvertimeRequestRead(
        id=req.id,
        employee_id=req.employee_id,
        employee_name=employee_name,
        requested_by=req.requested_by,
        requester=requester_read,
        date=req.date,
        hours=req.hours,
        start_time=req.start_time,
        end_time=req.end_time,
        time_range_label=format_time_range_label(req.start_time, req.end_time),
        justification=req.justification,
        status=req.status,
        approved_by=req.approved_by,
        approver=_user_brief(req.approver),
        approval_comment=req.approval_comment,
        created_at=req.created_at,
        updated_at=req.updated_at,
        history=hist,
    )


@router.get("", response_model=PaginatedResponse[OvertimeRequestRead])
async def list_overtime(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    employee_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PaginatedResponse[OvertimeRequestRead]:
    items, total = await svc.list_requests(
        db,
        current,
        page=page,
        page_size=page_size,
        status=status,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.list",
        entity_type="overtime_request",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_to_read(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/assignable-employees", response_model=PaginatedResponse[EmployeeRead])
async def list_assignable_employees(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("overtime.create"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    search: str | None = Query(None, description="Buscar por nombre o número de identificación"),
) -> PaginatedResponse[EmployeeRead]:
    """Empleados del equipo del líder (sin filtro por área) para el formulario de horas extra."""
    items, total = await svc.list_assignable_employees(
        db, current, page=page, page_size=page_size, search=search
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.assignable_employees",
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


@router.post("", response_model=OvertimeBatchCreateRead)
async def create_overtime(
    request: Request,
    body: OvertimeRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[
        User, Depends(require_any_permission("overtime.create"))
    ],
) -> OvertimeBatchCreateRead:
    items, hours_per_day, total_hours = await svc.create_requests(db, current, body)
    first_id = items[0].id if items else None
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.create",
        entity_type="overtime_request",
        entity_id=first_id,
        details={"count": len(items), "total_hours": str(total_hours)},
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["overtime", "notifications"])
    return OvertimeBatchCreateRead(
        items=[_to_read(r) for r in items],
        hours_per_day=hours_per_day,
        total_hours=total_hours,
    )


@router.get("/{request_id}", response_model=OvertimeRequestRead)
async def get_overtime(
    request: Request,
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> OvertimeRequestRead:
    r = await svc.get_request(db, request_id)
    if not r:
        from app.core.exceptions import not_found

        raise not_found()
    await svc.ensure_can_view(db, current, r)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.get",
        entity_type="overtime_request",
        entity_id=request_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _to_read(r)


@router.patch("/{request_id}", response_model=OvertimeRequestRead)
async def update_overtime(
    request: Request,
    request_id: int,
    body: OvertimeRequestUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[
        User, Depends(require_any_permission("overtime.edit"))
    ],
) -> OvertimeRequestRead:
    r = await svc.update_request(db, current, request_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.update",
        entity_type="overtime_request",
        entity_id=request_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["overtime", "notifications"])
    return _to_read(r)


@router.post("/{request_id}/decision", response_model=OvertimeRequestRead)
async def decide_overtime(
    request: Request,
    request_id: int,
    body: OvertimeApproveReject,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("overtime.approve"))],
) -> OvertimeRequestRead:
    r = await svc.approve_or_reject(db, current, request_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.decision",
        entity_type="overtime_request",
        entity_id=request_id,
        details={"approved": body.approved},
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["overtime", "notifications"])
    return _to_read(r)


@router.delete("/{request_id}")
async def delete_overtime(
    request: Request,
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("overtime.delete"))],
) -> dict[str, str]:
    await svc.delete_request(db, current, request_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="overtime.delete",
        entity_type="overtime_request",
        entity_id=request_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["overtime", "notifications"])
    return {"detail": "Operación correcta"}

import math
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.core.overtime_time import format_time_range_label
from app.db.session import get_db
from app.models.user import User
from app.realtime.notify import broadcast_data_changed
from app.schemas.common import PaginatedResponse
from app.schemas.overtime import UserBriefRead
from app.schemas.shift import ShiftScheduleCreate, ShiftScheduleRead, ShiftScheduleUpdate
from app.services import audit_service
from app.services import shift_service as svc

router = APIRouter()


def _user_brief(u) -> UserBriefRead | None:
    if u is None:
        return None
    return UserBriefRead(id=u.id, name=u.name, email=u.email)


def _to_read(row) -> ShiftScheduleRead:
    return ShiftScheduleRead(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=row.employee.name if row.employee else "",
        created_by=row.created_by,
        creator=_user_brief(row.creator),
        shift_date=row.shift_date,
        start_time=row.start_time,
        end_time=row.end_time,
        time_range_label=format_time_range_label(row.start_time, row.end_time),
        notes=row.notes,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=PaginatedResponse[ShiftScheduleRead])
async def list_shifts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("shifts.view"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    employee_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PaginatedResponse[ShiftScheduleRead]:
    items, total = await svc.list_shifts(
        db,
        current,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    await audit_service.write_audit(
        db, user_id=current.id, action="shifts.list",
        entity_type="shift_schedule", ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_to_read(r) for r in items], total=total, page=page, page_size=page_size, pages=pages,
    )


@router.post("", response_model=ShiftScheduleRead)
async def create_shift(
    request: Request,
    body: ShiftScheduleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("shifts.create"))],
) -> ShiftScheduleRead:
    row = await svc.create_shift(db, current, body)
    await audit_service.write_audit(
        db, user_id=current.id, action="shifts.create",
        entity_type="shift_schedule", entity_id=row.id, ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["shifts"])
    return _to_read(row)


@router.patch("/{shift_id}", response_model=ShiftScheduleRead)
async def update_shift(
    request: Request,
    shift_id: int,
    body: ShiftScheduleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("shifts.edit"))],
) -> ShiftScheduleRead:
    row = await svc.update_shift(db, current, shift_id, body)
    await audit_service.write_audit(
        db, user_id=current.id, action="shifts.update",
        entity_type="shift_schedule", entity_id=shift_id, ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["shifts"])
    return _to_read(row)


@router.delete("/{shift_id}")
async def delete_shift(
    request: Request,
    shift_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("shifts.delete"))],
) -> dict[str, str]:
    await svc.delete_shift(db, current, shift_id)
    await audit_service.write_audit(
        db, user_id=current.id, action="shifts.delete",
        entity_type="shift_schedule", entity_id=shift_id, ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["shifts"])
    return {"detail": "Operación correcta"}

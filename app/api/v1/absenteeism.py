import math
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.realtime.notify import broadcast_data_changed
from app.schemas.absenteeism import AbsenteeismRecordCreate, AbsenteeismRecordRead, AbsenteeismRecordUpdate
from app.schemas.common import PaginatedResponse
from app.schemas.overtime import UserBriefRead
from app.services import absenteeism_service as svc
from app.services import audit_service

router = APIRouter()


def _user_brief(u) -> UserBriefRead | None:
    if u is None:
        return None
    return UserBriefRead(id=u.id, name=u.name, email=u.email)


def _to_read(row) -> AbsenteeismRecordRead:
    return AbsenteeismRecordRead(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=row.employee.name if row.employee else "",
        created_by=row.created_by,
        creator=_user_brief(row.creator),
        classification=row.classification,
        start_date=row.start_date,
        end_date=row.end_date,
        days=row.days,
        justification=row.justification,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=PaginatedResponse[AbsenteeismRecordRead])
async def list_absenteeism(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("absenteeism.view"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    employee_id: int | None = None,
    classification: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PaginatedResponse[AbsenteeismRecordRead]:
    items, total = await svc.list_records(
        db,
        current,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        classification=classification,
        date_from=date_from,
        date_to=date_to,
    )
    await audit_service.write_audit(
        db, user_id=current.id, action="absenteeism.list",
        entity_type="absenteeism_record", ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_to_read(r) for r in items], total=total, page=page, page_size=page_size, pages=pages,
    )


@router.post("", response_model=AbsenteeismRecordRead)
async def create_absenteeism(
    request: Request,
    body: AbsenteeismRecordCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("absenteeism.create"))],
) -> AbsenteeismRecordRead:
    row = await svc.create_record(db, current, body)
    await audit_service.write_audit(
        db, user_id=current.id, action="absenteeism.create",
        entity_type="absenteeism_record", entity_id=row.id, ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["absenteeism"])
    return _to_read(row)


@router.patch("/{record_id}", response_model=AbsenteeismRecordRead)
async def update_absenteeism(
    request: Request,
    record_id: int,
    body: AbsenteeismRecordUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("absenteeism.edit"))],
) -> AbsenteeismRecordRead:
    row = await svc.update_record(db, current, record_id, body)
    await audit_service.write_audit(
        db, user_id=current.id, action="absenteeism.update",
        entity_type="absenteeism_record", entity_id=record_id, ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["absenteeism"])
    return _to_read(row)


@router.delete("/{record_id}")
async def delete_absenteeism(
    request: Request,
    record_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("absenteeism.delete"))],
) -> dict[str, str]:
    await svc.delete_record(db, current, record_id)
    await audit_service.write_audit(
        db, user_id=current.id, action="absenteeism.delete",
        entity_type="absenteeism_record", entity_id=record_id, ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["absenteeism"])
    return {"detail": "Operación correcta"}

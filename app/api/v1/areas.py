import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.area import AreaCreate, AreaRead, AreaUpdate
from app.schemas.common import PaginatedResponse
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import area_service as svc

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AreaRead])
async def list_areas(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> PaginatedResponse[AreaRead]:
    items, total = await svc.list_areas(db, page=page, page_size=page_size)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="areas.list",
        entity_type="area",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[AreaRead.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=AreaRead)
async def create_area(
    request: Request,
    body: AreaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("areas.create"))],
) -> AreaRead:
    a = await svc.create_area(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="areas.create",
        entity_type="area",
        entity_id=a.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["areas"])
    return AreaRead.model_validate(a)


@router.get("/{area_id}", response_model=AreaRead)
async def get_area(
    area_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> AreaRead:
    a = await svc.get_area(db, area_id)
    if not a:
        from app.core.exceptions import not_found

        raise not_found()
    return AreaRead.model_validate(a)


@router.patch("/{area_id}", response_model=AreaRead)
async def update_area(
    request: Request,
    area_id: int,
    body: AreaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("areas.edit"))],
) -> AreaRead:
    a = await svc.update_area(db, area_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="areas.update",
        entity_type="area",
        entity_id=area_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["areas"])
    return AreaRead.model_validate(a)


@router.delete("/{area_id}")
async def delete_area(
    request: Request,
    area_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("areas.delete"))],
) -> dict[str, str]:
    await svc.delete_area(db, area_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="areas.delete",
        entity_type="area",
        entity_id=area_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["areas"])
    return {"detail": "Operación correcta"}

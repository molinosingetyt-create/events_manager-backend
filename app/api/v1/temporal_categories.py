import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.incapacity_catalog import TemporalCategoryCreate, TemporalCategoryRead, TemporalCategoryUpdate
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import incapacity_catalog_service as svc

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TemporalCategoryRead])
async def list_items(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
) -> PaginatedResponse[TemporalCategoryRead]:
    items, total = await svc.list_temporal(db, page=page, page_size=page_size, status=status)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="temporal_categories.list",
        entity_type="temporal_category",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[TemporalCategoryRead.model_validate(x) for x in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=TemporalCategoryRead)
async def create_item(
    request: Request,
    body: TemporalCategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("catalog.settings"))],
) -> TemporalCategoryRead:
    row = await svc.create_temporal(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="temporal_categories.create",
        entity_type="temporal_category",
        entity_id=row.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["temporal_categories"])
    return TemporalCategoryRead.model_validate(row)


@router.get("/{item_id}", response_model=TemporalCategoryRead)
async def get_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> TemporalCategoryRead:
    row = await svc.get_temporal(db, item_id)
    if not row:
        from app.core.exceptions import not_found

        raise not_found()
    return TemporalCategoryRead.model_validate(row)


@router.patch("/{item_id}", response_model=TemporalCategoryRead)
async def update_item(
    request: Request,
    item_id: int,
    body: TemporalCategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("catalog.settings"))],
) -> TemporalCategoryRead:
    row = await svc.update_temporal(db, item_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="temporal_categories.update",
        entity_type="temporal_category",
        entity_id=item_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["temporal_categories"])
    return TemporalCategoryRead.model_validate(row)


@router.delete("/{item_id}")
async def delete_item(
    request: Request,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("catalog.settings"))],
) -> dict[str, str]:
    await svc.delete_temporal(db, item_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="temporal_categories.delete",
        entity_type="temporal_category",
        entity_id=item_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["temporal_categories"])
    return {"detail": "Operación correcta"}

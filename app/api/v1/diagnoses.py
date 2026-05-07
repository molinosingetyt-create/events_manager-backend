import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.incapacity_catalog import DiagnosisCreate, DiagnosisRead, DiagnosisUpdate
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import incapacity_catalog_service as svc

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DiagnosisRead])
async def list_items(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
) -> PaginatedResponse[DiagnosisRead]:
    items, total = await svc.list_diagnoses(db, page=page, page_size=page_size, status=status)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="diagnoses.list",
        entity_type="diagnosis",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[DiagnosisRead.model_validate(x) for x in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=DiagnosisRead)
async def create_item(
    request: Request,
    body: DiagnosisCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("catalog.settings"))],
) -> DiagnosisRead:
    row = await svc.create_diagnosis(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="diagnoses.create",
        entity_type="diagnosis",
        entity_id=row.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["diagnoses"])
    return DiagnosisRead.model_validate(row)


@router.get("/{item_id}", response_model=DiagnosisRead)
async def get_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> DiagnosisRead:
    row = await svc.get_diagnosis(db, item_id)
    if not row:
        from app.core.exceptions import not_found

        raise not_found()
    return DiagnosisRead.model_validate(row)


@router.patch("/{item_id}", response_model=DiagnosisRead)
async def update_item(
    request: Request,
    item_id: int,
    body: DiagnosisUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("catalog.settings"))],
) -> DiagnosisRead:
    row = await svc.update_diagnosis(db, item_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="diagnoses.update",
        entity_type="diagnosis",
        entity_id=item_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["diagnoses"])
    return DiagnosisRead.model_validate(row)


@router.delete("/{item_id}")
async def delete_item(
    request: Request,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("catalog.settings"))],
) -> dict[str, str]:
    await svc.delete_diagnosis(db, item_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="diagnoses.delete",
        entity_type="diagnosis",
        entity_id=item_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["diagnoses"])
    return {"detail": "Operación correcta"}

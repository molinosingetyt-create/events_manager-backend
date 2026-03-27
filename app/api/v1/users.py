import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import audit_service
from app.services import user_service as svc

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def me(current: Annotated[User, Depends(get_current_user)]) -> User:
    return current


@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    area_id: int | None = None,
    role: str | None = None,
) -> PaginatedResponse[UserRead]:
    items, total = await svc.list_users(db, page=page, page_size=page_size, area_id=area_id, role=role)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="users.list",
        entity_type="user",
        details={"page": page, "area_id": area_id},
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=UserRead)
async def create_user(
    request: Request,
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_roles(Role.ADMIN, Role.HR))],
) -> User:
    u = await svc.create_user(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="users.create",
        entity_type="user",
        entity_id=u.id,
        details={"email": body.email, "role": body.role.value},
        ip_address=client_ip(request),
    )
    await db.commit()
    return UserRead.model_validate(u)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> User:
    u = await svc.get_user(db, user_id)
    if not u:
        from app.core.exceptions import not_found

        raise not_found()
    if current.id != user_id and current.role not in (
        Role.ADMIN.value,
        Role.HR.value,
        Role.MANAGEMENT.value,
    ):
        from app.core.exceptions import forbidden

        raise forbidden()
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="users.get",
        entity_type="user",
        entity_id=user_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return u


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    request: Request,
    user_id: int,
    body: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_roles(Role.ADMIN, Role.HR))],
) -> User:
    u = await svc.update_user(db, user_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="users.update",
        entity_type="user",
        entity_id=user_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return UserRead.model_validate(u)


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_roles(Role.ADMIN, Role.HR))],
) -> dict[str, str]:
    await svc.delete_user(db, user_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="users.delete",
        entity_type="user",
        entity_id=user_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return {"detail": "Operación correcta"}

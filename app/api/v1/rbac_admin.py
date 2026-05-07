from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.permission import PermissionCreate, PermissionRead, PermissionUpdate
from app.schemas.profile import (
    ProfileCreate,
    ProfilePermissionsUpdate,
    ProfileRead,
    ProfileUpdate,
)
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import permission_service as perm_svc
from app.services import profile_service as prof_svc

router = APIRouter()


def _prof_read(p) -> ProfileRead:
    d = prof_svc._to_read(p)
    return ProfileRead.model_validate(d)


@router.get("/profiles", response_model=list[ProfileRead])
async def list_profiles(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[
        User,
        Depends(require_any_permission("security.profiles", "users.create", "users.edit")),
    ],
) -> list[ProfileRead]:
    rows = await prof_svc.list_profiles(db)
    return [_prof_read(p) for p in rows]


@router.post("/profiles", response_model=ProfileRead)
async def create_profile(
    request: Request,
    body: ProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.profiles"))],
) -> ProfileRead:
    p = await prof_svc.create_profile(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="profiles.create",
        entity_type="profile",
        entity_id=p.id,
        details={"code": p.code},
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return _prof_read(p)


@router.get("/profiles/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[
        User,
        Depends(require_any_permission("security.profiles", "users.create", "users.edit")),
    ],
) -> ProfileRead:
    p = await prof_svc.get_profile(db, profile_id)
    if not p:
        from app.core.exceptions import not_found

        raise not_found()
    return _prof_read(p)


@router.patch("/profiles/{profile_id}", response_model=ProfileRead)
async def update_profile(
    request: Request,
    profile_id: int,
    body: ProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.profiles"))],
) -> ProfileRead:
    p = await prof_svc.update_profile(db, profile_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="profiles.update",
        entity_type="profile",
        entity_id=profile_id,
        details={},
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return _prof_read(p)


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    request: Request,
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.profiles"))],
) -> dict[str, str]:
    await prof_svc.delete_profile(db, profile_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="profiles.delete",
        entity_type="profile",
        entity_id=profile_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return {"detail": "Operación correcta"}


@router.put("/profiles/{profile_id}/permissions", response_model=ProfileRead)
async def set_profile_permissions(
    request: Request,
    profile_id: int,
    body: ProfilePermissionsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.profiles"))],
) -> ProfileRead:
    p = await prof_svc.set_profile_permissions(db, profile_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="profiles.permissions",
        entity_type="profile",
        entity_id=profile_id,
        details={"n": len(body.permission_ids)},
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return _prof_read(p)


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[
        User,
        Depends(require_any_permission("security.permissions", "security.profiles")),
    ],
) -> list[PermissionRead]:
    rows = await perm_svc.list_permissions(db)
    return [PermissionRead.model_validate(x) for x in rows]


@router.post("/permissions", response_model=PermissionRead)
async def create_permission(
    request: Request,
    body: PermissionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.permissions"))],
) -> PermissionRead:
    p = await perm_svc.create_permission(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="permissions.create",
        entity_type="permission",
        entity_id=p.id,
        details={"code": p.code},
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return PermissionRead.model_validate(p)


@router.patch("/permissions/{permission_id}", response_model=PermissionRead)
async def update_permission(
    request: Request,
    permission_id: int,
    body: PermissionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.permissions"))],
) -> PermissionRead:
    p = await perm_svc.update_permission(db, permission_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="permissions.update",
        entity_type="permission",
        entity_id=permission_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return PermissionRead.model_validate(p)


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    request: Request,
    permission_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("security.permissions"))],
) -> dict[str, str]:
    await perm_svc.delete_permission(db, permission_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="permissions.delete",
        entity_type="permission",
        entity_id=permission_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["rbac"])
    return {"detail": "Operación correcta"}

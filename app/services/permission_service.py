from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import bad_request, not_found
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate


async def list_permissions(db: AsyncSession) -> list[Permission]:
    r = await db.execute(select(Permission).order_by(Permission.sort_order, Permission.id))
    return list(r.scalars().all())


async def get_permission(db: AsyncSession, permission_id: int) -> Permission | None:
    r = await db.execute(select(Permission).where(Permission.id == permission_id))
    return r.scalar_one_or_none()


async def create_permission(db: AsyncSession, data: PermissionCreate) -> Permission:
    dup = await db.execute(select(Permission).where(Permission.code == data.code))
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe un permiso con ese código")

    mx = await db.execute(select(Permission.sort_order).order_by(Permission.sort_order.desc()).limit(1))
    row = mx.scalar_one_or_none()
    next_order = (row or 0) + 1

    p = Permission(
        code=data.code,
        name=data.name,
        description=data.description,
        is_system=False,
        sort_order=next_order,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def update_permission(db: AsyncSession, permission_id: int, data: PermissionUpdate) -> Permission:
    p = await get_permission(db, permission_id)
    if not p:
        raise not_found("Permiso no encontrado")

    if data.name is not None:
        p.name = data.name
    if data.description is not None:
        p.description = data.description
    if data.sort_order is not None:
        p.sort_order = data.sort_order

    await db.commit()
    await db.refresh(p)
    return p


async def delete_permission(db: AsyncSession, permission_id: int) -> None:
    p = await get_permission(db, permission_id)
    if not p:
        raise not_found("Permiso no encontrado")
    if p.is_system:
        raise bad_request("No se puede eliminar un permiso del sistema")

    await db.execute(delete(Permission).where(Permission.id == permission_id))
    await db.commit()

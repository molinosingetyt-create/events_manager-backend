from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, not_found
from app.models.permission import Permission
from app.models.profile import Profile, profile_permissions
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfilePermissionsUpdate, ProfileUpdate


async def get_profile_by_code(db: AsyncSession, code: str) -> Profile | None:
    r = await db.execute(select(Profile).where(Profile.code == code))
    return r.scalar_one_or_none()


async def get_profile(db: AsyncSession, profile_id: int) -> Profile | None:
    r = await db.execute(
        select(Profile)
        .options(selectinload(Profile.permissions))
        .where(Profile.id == profile_id)
    )
    return r.scalar_one_or_none()


def _to_read(p: Profile) -> dict:
    perm_ids = [x.id for x in (p.permissions or [])]
    return {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "description": p.description,
        "behavior_key": p.behavior_key,
        "is_system": p.is_system,
        "sort_order": p.sort_order,
        "permission_ids": perm_ids,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


async def list_profiles(db: AsyncSession) -> list[Profile]:
    r = await db.execute(
        select(Profile)
        .options(selectinload(Profile.permissions))
        .order_by(Profile.sort_order, Profile.id)
    )
    return list(r.scalars().unique().all())


async def create_profile(db: AsyncSession, data: ProfileCreate) -> Profile:
    code_u = data.code.upper()
    dup = await db.execute(select(Profile).where(Profile.code == code_u))
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe un perfil con ese código")

    p = Profile(
        code=code_u,
        name=data.name,
        description=data.description,
        behavior_key=data.behavior_key.upper(),
        is_system=False,
        sort_order=0,
    )
    db.add(p)
    await db.flush()

    if data.permission_ids:
        await _set_permissions(db, p.id, data.permission_ids)

    await db.commit()
    out = await get_profile(db, p.id)
    assert out
    return out


async def update_profile(db: AsyncSession, profile_id: int, data: ProfileUpdate) -> Profile:
    p = await get_profile(db, profile_id)
    if not p:
        raise not_found("Perfil no encontrado")

    if data.name is not None:
        p.name = data.name
    if data.description is not None:
        p.description = data.description
    if data.behavior_key is not None:
        p.behavior_key = data.behavior_key.upper()
    if data.sort_order is not None:
        p.sort_order = data.sort_order

    await db.commit()
    out = await get_profile(db, profile_id)
    assert out
    return out


async def delete_profile(db: AsyncSession, profile_id: int) -> None:
    p = await get_profile(db, profile_id)
    if not p:
        raise not_found("Perfil no encontrado")
    if p.is_system:
        raise bad_request("No se puede eliminar un perfil del sistema")

    cnt = (await db.execute(select(func.count()).select_from(User).where(User.profile_id == profile_id))).scalar_one()
    if cnt and int(cnt) > 0:
        raise bad_request("Hay usuarios asignados a este perfil; reasígnelos antes")

    await db.execute(delete(Profile).where(Profile.id == profile_id))
    await db.commit()


async def _set_permissions(db: AsyncSession, profile_id: int, permission_ids: list[int]) -> None:
    await db.execute(delete(profile_permissions).where(profile_permissions.c.profile_id == profile_id))
    if not permission_ids:
        return
    r = await db.execute(select(Permission.id).where(Permission.id.in_(permission_ids)))
    found = {row[0] for row in r.all()}
    if found != set(permission_ids):
        raise bad_request("Algún permiso no existe")
    for pid in permission_ids:
        await db.execute(
            insert(profile_permissions).values(profile_id=profile_id, permission_id=pid)
        )


async def set_profile_permissions(
    db: AsyncSession, profile_id: int, body: ProfilePermissionsUpdate
) -> Profile:
    p = await get_profile(db, profile_id)
    if not p:
        raise not_found("Perfil no encontrado")

    await _set_permissions(db, profile_id, body.permission_ids)
    await db.commit()
    out = await get_profile(db, profile_id)
    assert out
    return out

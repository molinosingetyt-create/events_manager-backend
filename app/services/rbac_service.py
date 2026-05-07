"""Resolución de permisos en base de datos y clave de comportamiento (ámbito por rol)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import Role
from app.models.permission import Permission
from app.models.profile import Profile, profile_permissions
from app.models.user import User


def behavior_key(user: User) -> str:
    """Clave usada por servicios (área, alcance) — coincide con Role para perfiles estándar."""
    if getattr(user, "profile", None) is not None and user.profile is not None:
        return user.profile.behavior_key
    return user.role


def is_behavior(user: User, *keys: Role | str) -> bool:
    bk = behavior_key(user)
    wanted = {k.value if isinstance(k, Role) else str(k) for k in keys}
    return bk in wanted


async def permission_codes_for_user(db: AsyncSession, user: User) -> set[str]:
    r = await db.execute(
        select(Permission.code)
        .join(profile_permissions, profile_permissions.c.permission_id == Permission.id)
        .where(profile_permissions.c.profile_id == user.profile_id)
    )
    return {row[0] for row in r.all()}


async def permission_briefs_for_user(db: AsyncSession, user: User) -> list[tuple[str, str]]:
    """Pares (code, name) ordenados por nombre para mostrar en UI."""
    r = await db.execute(
        select(Permission.code, Permission.name)
        .join(profile_permissions, profile_permissions.c.permission_id == Permission.id)
        .where(profile_permissions.c.profile_id == user.profile_id)
        .order_by(Permission.name.asc(), Permission.code.asc())
    )
    return [(row[0], row[1]) for row in r.all()]


async def user_has_any_permission(
    db: AsyncSession,
    user: User,
    *codes: str,
) -> bool:
    if not codes:
        return True
    have = await permission_codes_for_user(db, user)
    return bool(have.intersection(codes))


async def user_has_all_permissions(
    db: AsyncSession,
    user: User,
    *codes: str,
) -> bool:
    if not codes:
        return True
    have = await permission_codes_for_user(db, user)
    return set(codes).issubset(have)


async def load_user_with_profile(db: AsyncSession, user_id: int) -> User | None:
    r = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    return r.scalar_one_or_none()

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, not_found
from app.core.security import get_password_hash
from app.models.enums import EntityStatus, Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    r = await db.execute(select(User).where(User.id == user_id))
    return r.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    area_id: int | None = None,
    role: str | None = None,
) -> tuple[list[User], int]:
    q = select(User)
    count_q = select(func.count()).select_from(User)
    if area_id is not None:
        q = q.where(User.area_id == area_id)
        count_q = count_q.where(User.area_id == area_id)
    if role is not None:
        q = q.where(User.role == role)
        count_q = count_q.where(User.role == role)
    total = (await db.execute(count_q)).scalar_one()
    q = q.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise bad_request("El correo ya está registrado")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        role=data.role.value,
        area_id=data.area_id,
        status=data.status.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await get_user(db, user_id)
    if not user:
        raise not_found("Usuario no encontrado")

    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        dup = await db.execute(select(User).where(User.email == data.email, User.id != user_id))
        if dup.scalar_one_or_none():
            raise bad_request("El correo ya está en uso")
        user.email = data.email
    if data.password is not None:
        user.hashed_password = get_password_hash(data.password)
    if data.role is not None:
        user.role = data.role.value
    if data.area_id is not None:
        user.area_id = data.area_id
    if data.status is not None:
        user.status = data.status.value

    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user(db, user_id)
    if not user:
        raise not_found("Usuario no encontrado")
    user.status = EntityStatus.INACTIVE.value
    await db.commit()


def can_create_users(actor: User) -> bool:
    return actor.role in (Role.ADMIN.value, Role.HR.value)

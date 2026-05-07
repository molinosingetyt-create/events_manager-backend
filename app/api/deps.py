from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import unauthorized
from app.core.security import decode_token, verify_token_type
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.services import rbac_service

security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        return None
    if not verify_token_type(payload, "access"):
        return None
    uid = int(payload.get("sub", 0))
    r = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == uid)
    )
    return r.scalar_one_or_none()


async def get_current_user(
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> User:
    if not user:
        raise unauthorized()
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Compatibilidad: exige que behavior_key coincida con uno de los roles clásicos."""
    allowed = {r.value for r in roles}

    async def _inner(user: User = Depends(get_current_user)) -> User:
        if rbac_service.behavior_key(user) not in allowed:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user

    return _inner


def require_any_permission(*codes: str) -> Callable[..., User]:
    """El usuario debe tener al menos uno de los permisos indicados."""

    async def _inner(
        user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        if not await rbac_service.user_has_any_permission(db, user, *codes):
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user

    return _inner


def client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None

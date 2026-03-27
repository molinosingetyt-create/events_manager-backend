import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)
from app.models.enums import EntityStatus
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenPair
from app.services import audit_service


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User | None:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or user.status != EntityStatus.ACTIVE.value:
        return None
    if not verify_password(data.password, user.hashed_password):
        return None
    return user


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def login(
    db: AsyncSession,
    data: LoginRequest,
    *,
    ip_address: str | None = None,
) -> tuple[User, TokenPair]:
    user = await authenticate_user(db, data)
    if not user:
        raise bad_request("Correo o contraseña incorrectos")

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))

    from app.core.config import get_settings

    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh),
        expires_at=expires,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rt)
    await audit_service.write_audit(
        db,
        user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        details={"email": data.email},
        ip_address=ip_address,
    )
    await db.commit()
    await db.refresh(rt)

    return user, TokenPair(access_token=access, refresh_token=refresh)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise unauthorized("Token de actualización no válido")

    if not verify_token_type(payload, "refresh"):
        raise unauthorized("Tipo de token no válido")

    uid = int(payload.get("sub", 0))
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    row = result.scalar_one_or_none()
    if not row or row.user_id != uid:
        raise unauthorized("Token de actualización inválido o revocado")

    user_result = await db.execute(select(User).where(User.id == uid))
    user = user_result.scalar_one_or_none()
    if not user or user.status != EntityStatus.ACTIVE.value:
        raise unauthorized("Usuario inactivo")

    row.revoked_at = datetime.now(timezone.utc)
    access = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))
    from app.core.config import get_settings

    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh),
        expires_at=expires,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_rt)
    await db.commit()

    return TokenPair(access_token=access, refresh_token=new_refresh)

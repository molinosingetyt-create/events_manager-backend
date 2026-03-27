from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from app.services import auth_service as auth_svc

router = APIRouter()


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    _, tokens = await auth_svc.login(db, body, ip_address=client_ip(request))
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    return await auth_svc.refresh_tokens(db, body.refresh_token)

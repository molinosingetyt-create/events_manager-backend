from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import not_found
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationRead, UnreadCountResponse
from app.realtime.notify import broadcast_data_changed
from app.services import notification_service as notif_svc

router = APIRouter()


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> UnreadCountResponse:
    c = await notif_svc.count_unread(db, current.id)
    return UnreadCountResponse(count=c)


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    unread_only: bool = Query(False),
) -> list[NotificationRead]:
    rows = await notif_svc.list_for_user(db, current.id, unread_only=unread_only)
    return [NotificationRead(**notif_svc.to_read_model(n)) for n in rows]


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> NotificationRead:
    n = await notif_svc.mark_read(db, current.id, notification_id)
    if not n:
        raise not_found("Notificación no encontrada")
    await db.commit()
    await db.refresh(n)
    await broadcast_data_changed(["notifications"])
    return NotificationRead(**notif_svc.to_read_model(n))


@router.post("/read-all")
async def mark_all_notifications_read(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> dict:
    await notif_svc.mark_all_read(db, current.id)
    await db.commit()
    await broadcast_data_changed(["notifications"])
    return {"ok": True}

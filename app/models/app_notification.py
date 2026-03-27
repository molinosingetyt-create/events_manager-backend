from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AppNotification(Base):
    """Notificación in-app por usuario (lectura = desaparece del contador)."""

    __tablename__ = "app_notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "overtime_request_id", "kind", name="uq_app_notif_user_ot_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    overtime_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("overtime_requests.id", ondelete="CASCADE"), nullable=True, index=True
    )
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")

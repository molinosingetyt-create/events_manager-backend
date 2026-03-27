from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class OvertimeRequest(Base, TimestampMixin, StatusMixin):
    __tablename__ = "overtime_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)

    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approval_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="overtime_requests")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    history_entries: Mapped[list["OvertimeRequestHistory"]] = relationship(
        "OvertimeRequestHistory",
        back_populates="request",
        order_by="OvertimeRequestHistory.created_at",
    )


class OvertimeRequestHistory(Base):
    __tablename__ = "overtime_request_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("overtime_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    snapshot: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    request: Mapped["OvertimeRequest"] = relationship("OvertimeRequest", back_populates="history_entries")
    user: Mapped[Optional["User"]] = relationship("User")

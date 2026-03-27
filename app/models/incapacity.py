from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class IncapacityNote(Base, TimestampMixin, StatusMixin):
    __tablename__ = "incapacity_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    support: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    employee: Mapped["Employee"] = relationship("Employee", back_populates="incapacity_notes")
    creator: Mapped["User"] = relationship("User")
    history_entries: Mapped[list["IncapacityNoteHistory"]] = relationship(
        "IncapacityNoteHistory",
        back_populates="incapacity_note",
        order_by="IncapacityNoteHistory.created_at",
    )
    comments: Mapped[list["IncapacityComment"]] = relationship(
        "IncapacityComment",
        back_populates="incapacity",
        order_by="IncapacityComment.created_at",
    )


class IncapacityNoteHistory(Base):
    __tablename__ = "incapacity_note_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incapacity_id: Mapped[int] = mapped_column(
        ForeignKey("incapacity_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    snapshot: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    incapacity_note: Mapped["IncapacityNote"] = relationship(
        "IncapacityNote", back_populates="history_entries"
    )
    user: Mapped[Optional["User"]] = relationship("User")


class IncapacityComment(Base):
    __tablename__ = "incapacity_comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incapacity_id: Mapped[int] = mapped_column(
        ForeignKey("incapacity_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    incapacity: Mapped["IncapacityNote"] = relationship("IncapacityNote", back_populates="comments")
    user: Mapped["User"] = relationship("User")

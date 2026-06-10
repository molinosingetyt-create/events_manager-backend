from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.incapacity_catalog import Diagnosis, EpsArlEntity, TemporalCategory
    from app.models.user import User


class IncapacityExtension(Base, TimestampMixin):
    """Prórroga asociada a una incapacidad (fechas obligatorias; imagen y nota opcionales)."""

    __tablename__ = "incapacity_extensions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incapacity_id: Mapped[int] = mapped_column(
        ForeignKey("incapacity_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    incapacity_note: Mapped["IncapacityNote"] = relationship(
        "IncapacityNote", back_populates="extensions"
    )
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])


class IncapacityNote(Base, TimestampMixin, StatusMixin):
    __tablename__ = "incapacity_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    support: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    temporal_category_id: Mapped[int] = mapped_column(
        ForeignKey("temporal_categories.id", ondelete="RESTRICT"), nullable=False
    )
    eps_arl_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("eps_arl_entities.id", ondelete="SET NULL"), nullable=True
    )
    diagnosis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="SET NULL"), nullable=True
    )
    long_absence_document_kind: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    long_absence_second_file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    long_absence_eps_transcribed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    causation_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    causation_month: Mapped[Optional[int]] = mapped_column(nullable=True)
    causation_half: Mapped[Optional[int]] = mapped_column(nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="incapacity_notes")
    temporal_category: Mapped["TemporalCategory"] = relationship(
        "TemporalCategory", back_populates="incapacity_notes"
    )
    eps_arl: Mapped[Optional["EpsArlEntity"]] = relationship(
        "EpsArlEntity", back_populates="incapacity_notes"
    )
    diagnosis: Mapped[Optional["Diagnosis"]] = relationship("Diagnosis", back_populates="incapacity_notes")
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
    extensions: Mapped[list["IncapacityExtension"]] = relationship(
        "IncapacityExtension",
        back_populates="incapacity_note",
        order_by="IncapacityExtension.id",
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

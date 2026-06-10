from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class EmployeeEducation(Base, TimestampMixin):
    __tablename__ = "employee_education"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    education_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    program: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="education_records")


class EmployeeTraining(Base, TimestampMixin):
    __tablename__ = "employee_training"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    training_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="training_records")


class EmployeePriorJob(Base, TimestampMixin):
    __tablename__ = "employee_prior_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    economic_sector: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    leave_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference_phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="prior_jobs")

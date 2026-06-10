"""Campos personalizados y novedades de nómina (fase 6)."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class EmployeeCustomFieldDef(Base, TimestampMixin):
    __tablename__ = "employee_custom_field_defs"
    __table_args__ = (UniqueConstraint("field_key", name="uq_employee_custom_field_defs_field_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    section: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    options_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    values: Mapped[list["EmployeeCustomFieldValue"]] = relationship(
        "EmployeeCustomFieldValue",
        back_populates="field_def",
        cascade="all, delete-orphan",
    )


class EmployeeCustomFieldValue(Base, TimestampMixin):
    __tablename__ = "employee_custom_field_values"
    __table_args__ = (
        UniqueConstraint("employee_id", "field_def_id", name="uq_employee_custom_field_values_emp_field"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_def_id: Mapped[int] = mapped_column(
        ForeignKey("employee_custom_field_defs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="custom_field_values")
    field_def: Mapped["EmployeeCustomFieldDef"] = relationship(
        "EmployeeCustomFieldDef", back_populates="values"
    )


class EmployeePayrollEntry(Base, TimestampMixin):
    __tablename__ = "employee_payroll_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    concept_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    reference_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="payroll_entries")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

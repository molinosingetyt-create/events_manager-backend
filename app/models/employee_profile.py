from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class EmployeePersonal(Base, TimestampMixin):
    __tablename__ = "employee_personal"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        primary_key=True,
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    second_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_surname: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    second_surname: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    children_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    residence_city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    residence_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    personal_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    corporate_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    blood_type: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    rh_factor: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="personal")


class EmployeeDependent(Base, TimestampMixin):
    __tablename__ = "employee_dependents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parentesco: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    schooling: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="dependents")


class EmployeeLabor(Base, TimestampMixin):
    __tablename__ = "employee_labor"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        primary_key=True,
    )
    linkage_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    temp_agency_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_site_city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    hierarchical_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    contract_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    base_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    work_schedule_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    work_modality: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    eps_affiliation_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    eps_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pension_fund: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    severance_fund: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    family_compensation_box: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    arl_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    arl_risk_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    bank_account_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    collaborator_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="labor")

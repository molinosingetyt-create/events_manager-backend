"""Competencias, SST e historial interno (fase 4)."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class EmployeeLanguage(Base, TimestampMixin):
    __tablename__ = "employee_languages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="languages")


class EmployeeSoftwareSkill(Base, TimestampMixin):
    __tablename__ = "employee_software_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    proficiency: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="software_skills")


class EmployeeDrivingLicense(Base, TimestampMixin):
    __tablename__ = "employee_driving_licenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="driving_licenses")


class EmployeeWorkSstCert(Base, TimestampMixin):
    __tablename__ = "employee_work_sst_certs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="work_sst_certs")


class EmployeeCompetencyEvaluation(Base, TimestampMixin):
    __tablename__ = "employee_competency_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_label: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evaluator_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="competency_evaluations")


class EmployeeSstProfile(Base, TimestampMixin):
    __tablename__ = "employee_sst_profiles"
    __table_args__ = (UniqueConstraint("employee_id", name="uq_employee_sst_profiles_employee_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entry_exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    entry_medical_concept: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entry_restrictions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occupational_disease: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_medical_restrictions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="sst_profile", uselist=False)


class EmployeeSstPeriodicExam(Base, TimestampMixin):
    __tablename__ = "employee_sst_periodic_exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="sst_periodic_exams")


class EmployeeSstIncapacity(Base, TimestampMixin):
    __tablename__ = "employee_sst_incapacities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    origin: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="sst_incapacities")


class EmployeeSstAccident(Base, TimestampMixin):
    __tablename__ = "employee_sst_accidents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occurred_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lost_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="sst_accidents")


class EmployeeSstPpe(Base, TimestampMixin):
    __tablename__ = "employee_sst_ppe"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    delivered_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    receipt_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="sst_ppe")


class EmployeeContractHistory(Base, TimestampMixin):
    __tablename__ = "employee_contract_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="contract_history")


class EmployeeSalaryHistory(Base, TimestampMixin):
    __tablename__ = "employee_salary_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    previous_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    new_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="salary_history")


class EmployeePerformanceReview(Base, TimestampMixin):
    __tablename__ = "employee_performance_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_label: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evaluator_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="performance_reviews")


class EmployeeRecognition(Base, TimestampMixin):
    __tablename__ = "employee_recognitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    recognized_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="recognitions")


class EmployeeDisciplinaryAction(Base, TimestampMixin):
    __tablename__ = "employee_disciplinary_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="disciplinary_actions")


class EmployeeAbsenceRecord(Base, TimestampMixin):
    __tablename__ = "employee_absence_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    absence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="absence_records")

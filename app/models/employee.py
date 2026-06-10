from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.employee_career import EmployeeEducation, EmployeePriorJob, EmployeeTraining
    from app.models.employee_custom import (
        EmployeeCustomFieldValue,
        EmployeePayrollEntry,
    )
    from app.models.employee_extended import (
        EmployeeAbsenceRecord,
        EmployeeCompetencyEvaluation,
        EmployeeContractHistory,
        EmployeeDisciplinaryAction,
        EmployeeDrivingLicense,
        EmployeeLanguage,
        EmployeePerformanceReview,
        EmployeeRecognition,
        EmployeeSalaryHistory,
        EmployeeSoftwareSkill,
        EmployeeSstAccident,
        EmployeeSstIncapacity,
        EmployeeSstPeriodicExam,
        EmployeeSstPpe,
        EmployeeSstProfile,
        EmployeeWorkSstCert,
    )
    from app.models.employee_document import EmployeeDocument
    from app.models.employee_profile import EmployeeDependent, EmployeeLabor, EmployeePersonal
    from app.models.absenteeism import AbsenteeismRecord
    from app.models.incapacity import IncapacityNote
    from app.models.shift import ShiftSchedule
    from app.models.incapacity_catalog import TemporalCategory
    from app.models.overtime import OvertimeRequest
    from app.models.user import User


class Employee(Base, TimestampMixin, StatusMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identification_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    position: Mapped[str] = mapped_column(String(255), nullable=False)

    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False)
    leader_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    temporal_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("temporal_categories.id", ondelete="RESTRICT"), nullable=True
    )

    area: Mapped["Area"] = relationship("Area", back_populates="employees")
    leader_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[leader_id], back_populates="led_employees"
    )
    temporal_category: Mapped[Optional["TemporalCategory"]] = relationship(
        "TemporalCategory", back_populates="employees"
    )
    overtime_requests: Mapped[list["OvertimeRequest"]] = relationship(
        "OvertimeRequest", back_populates="employee"
    )
    incapacity_notes: Mapped[list["IncapacityNote"]] = relationship(
        "IncapacityNote", back_populates="employee"
    )
    absenteeism_records: Mapped[list["AbsenteeismRecord"]] = relationship(
        "AbsenteeismRecord", back_populates="employee"
    )
    shift_schedules: Mapped[list["ShiftSchedule"]] = relationship(
        "ShiftSchedule", back_populates="employee"
    )
    personal: Mapped[Optional["EmployeePersonal"]] = relationship(
        "EmployeePersonal",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
    )
    labor: Mapped[Optional["EmployeeLabor"]] = relationship(
        "EmployeeLabor",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
    )
    dependents: Mapped[list["EmployeeDependent"]] = relationship(
        "EmployeeDependent",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeDependent.id",
    )
    documents: Mapped[list["EmployeeDocument"]] = relationship(
        "EmployeeDocument",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeDocument.created_at",
    )
    education_records: Mapped[list["EmployeeEducation"]] = relationship(
        "EmployeeEducation",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeEducation.id",
    )
    training_records: Mapped[list["EmployeeTraining"]] = relationship(
        "EmployeeTraining",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeTraining.id",
    )
    prior_jobs: Mapped[list["EmployeePriorJob"]] = relationship(
        "EmployeePriorJob",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeePriorJob.id",
    )
    languages: Mapped[list["EmployeeLanguage"]] = relationship(
        "EmployeeLanguage",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeLanguage.id",
    )
    software_skills: Mapped[list["EmployeeSoftwareSkill"]] = relationship(
        "EmployeeSoftwareSkill",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeSoftwareSkill.id",
    )
    driving_licenses: Mapped[list["EmployeeDrivingLicense"]] = relationship(
        "EmployeeDrivingLicense",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeDrivingLicense.id",
    )
    work_sst_certs: Mapped[list["EmployeeWorkSstCert"]] = relationship(
        "EmployeeWorkSstCert",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeWorkSstCert.id",
    )
    competency_evaluations: Mapped[list["EmployeeCompetencyEvaluation"]] = relationship(
        "EmployeeCompetencyEvaluation",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeCompetencyEvaluation.id",
    )
    sst_profile: Mapped[Optional["EmployeeSstProfile"]] = relationship(
        "EmployeeSstProfile",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sst_periodic_exams: Mapped[list["EmployeeSstPeriodicExam"]] = relationship(
        "EmployeeSstPeriodicExam",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeSstPeriodicExam.id",
    )
    sst_incapacities: Mapped[list["EmployeeSstIncapacity"]] = relationship(
        "EmployeeSstIncapacity",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeSstIncapacity.id",
    )
    sst_accidents: Mapped[list["EmployeeSstAccident"]] = relationship(
        "EmployeeSstAccident",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeSstAccident.id",
    )
    sst_ppe: Mapped[list["EmployeeSstPpe"]] = relationship(
        "EmployeeSstPpe",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeSstPpe.id",
    )
    contract_history: Mapped[list["EmployeeContractHistory"]] = relationship(
        "EmployeeContractHistory",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeContractHistory.id",
    )
    salary_history: Mapped[list["EmployeeSalaryHistory"]] = relationship(
        "EmployeeSalaryHistory",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeSalaryHistory.id",
    )
    performance_reviews: Mapped[list["EmployeePerformanceReview"]] = relationship(
        "EmployeePerformanceReview",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeePerformanceReview.id",
    )
    recognitions: Mapped[list["EmployeeRecognition"]] = relationship(
        "EmployeeRecognition",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeRecognition.id",
    )
    disciplinary_actions: Mapped[list["EmployeeDisciplinaryAction"]] = relationship(
        "EmployeeDisciplinaryAction",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeDisciplinaryAction.id",
    )
    absence_records: Mapped[list["EmployeeAbsenceRecord"]] = relationship(
        "EmployeeAbsenceRecord",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeAbsenceRecord.id",
    )
    custom_field_values: Mapped[list["EmployeeCustomFieldValue"]] = relationship(
        "EmployeeCustomFieldValue",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeeCustomFieldValue.field_def_id",
    )
    payroll_entries: Mapped[list["EmployeePayrollEntry"]] = relationship(
        "EmployeePayrollEntry",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeePayrollEntry.period_month",
    )

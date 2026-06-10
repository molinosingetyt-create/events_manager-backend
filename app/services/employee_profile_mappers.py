"""Mapeo ORM → schemas del expediente HR."""

from datetime import date

from decimal import Decimal

from app.models.employee_career import EmployeeEducation, EmployeePriorJob, EmployeeTraining
from app.models.employee_document import EmployeeDocument
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
from app.models.employee_profile import EmployeeDependent, EmployeeLabor, EmployeePersonal
from app.schemas.employee_profile import (
    DOCUMENT_KIND_LABELS,
    EmployeeAbsenceRecordRead,
    EmployeeCompetencyEvaluationRead,
    EmployeeContractHistoryRead,
    EmployeeDependentRead,
    EmployeeDisciplinaryActionRead,
    EmployeeDocumentRead,
    EmployeeDrivingLicenseRead,
    EmployeeEducationRead,
    EmployeeLaborRead,
    EmployeeLanguageRead,
    EmployeePerformanceReviewRead,
    EmployeePersonalRead,
    EmployeePriorJobRead,
    EmployeeRecognitionRead,
    EmployeeSalaryHistoryRead,
    EmployeeSoftwareSkillRead,
    EmployeeSstAccidentRead,
    EmployeeSstIncapacityRead,
    EmployeeSstPeriodicExamRead,
    EmployeeSstPpeRead,
    EmployeeSstProfileRead,
    EmployeeTrainingRead,
    EmployeeWorkSstCertRead,
)


def calc_age(birth: date | None) -> int | None:
    if birth is None:
        return None
    today = date.today()
    years = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        years -= 1
    return max(0, years)


def calc_seniority(hire: date | None) -> str | None:
    if hire is None:
        return None
    today = date.today()
    years = today.year - hire.year
    months = today.month - hire.month
    days = today.day - hire.day
    if days < 0:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    if years < 0:
        return None
    parts: list[str] = []
    if years:
        parts.append(f"{years} año{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} mes{'es' if months != 1 else ''}")
    if not parts:
        parts.append(f"{max(0, days)} día{'s' if days != 1 else ''}")
    return ", ".join(parts)


def effective_document_status(row: EmployeeDocument, today: date | None = None) -> str:
    today = today or date.today()
    if row.status == "vigente" and row.expires_at is not None and row.expires_at < today:
        return "vencido"
    return row.status


def dependent_read(d: EmployeeDependent) -> EmployeeDependentRead:
    return EmployeeDependentRead(
        id=d.id,
        full_name=d.full_name,
        relationship=d.parentesco,
        birth_date=d.birth_date,
        schooling=d.schooling,
    )


def document_read(row: EmployeeDocument) -> EmployeeDocumentRead:
    uploader = row.uploaded_by.name if row.uploaded_by is not None else None
    return EmployeeDocumentRead(
        id=row.id,
        employee_id=row.employee_id,
        document_kind=row.document_kind,  # type: ignore[arg-type]
        document_kind_label=DOCUMENT_KIND_LABELS.get(row.document_kind, row.document_kind),
        display_name=row.display_name,
        file_url=row.file_url,
        content_type=row.content_type,
        file_size=row.file_size,
        status=effective_document_status(row),  # type: ignore[arg-type]
        expires_at=row.expires_at,
        uploaded_by_id=row.uploaded_by_id,
        uploaded_by_name=uploader,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def personal_read(p: EmployeePersonal | None) -> EmployeePersonalRead:
    if p is None:
        return EmployeePersonalRead()
    return EmployeePersonalRead(
        first_name=p.first_name,
        second_name=p.second_name,
        first_surname=p.first_surname,
        second_surname=p.second_surname,
        document_type=p.document_type,  # type: ignore[arg-type]
        birth_date=p.birth_date,
        age_years=calc_age(p.birth_date),
        gender=p.gender,
        marital_status=p.marital_status,
        children_count=p.children_count,
        residence_city=p.residence_city,
        residence_address=p.residence_address,
        neighborhood=p.neighborhood,
        phone=p.phone,
        personal_email=p.personal_email,
        corporate_email=p.corporate_email,
        photo_url=p.photo_url,
        blood_type=p.blood_type,
        rh_factor=p.rh_factor,
    )


def labor_read(l: EmployeeLabor | None) -> EmployeeLaborRead:
    if l is None:
        return EmployeeLaborRead()
    return EmployeeLaborRead(
        linkage_type=l.linkage_type,  # type: ignore[arg-type]
        temp_agency_name=l.temp_agency_name,
        work_site_city=l.work_site_city,
        hierarchical_level=l.hierarchical_level,  # type: ignore[arg-type]
        hire_date=l.hire_date,
        seniority_text=calc_seniority(l.hire_date),
        contract_type=l.contract_type,  # type: ignore[arg-type]
        contract_end_date=l.contract_end_date,
        base_salary=l.base_salary,
        work_schedule_type=l.work_schedule_type,
        work_modality=l.work_modality,  # type: ignore[arg-type]
        eps_affiliation_number=l.eps_affiliation_number,
        eps_name=l.eps_name,
        pension_fund=l.pension_fund,
        severance_fund=l.severance_fund,
        family_compensation_box=l.family_compensation_box,
        arl_name=l.arl_name,
        arl_risk_level=l.arl_risk_level,
        bank_name=l.bank_name,
        bank_account_type=l.bank_account_type,
        bank_account_number=l.bank_account_number,
        collaborator_status=l.collaborator_status,  # type: ignore[arg-type]
        notes=l.notes,
    )


def calc_job_duration(start: date | None, end: date | None) -> str | None:
    if start is None:
        return None
    end_d = end or date.today()
    if end_d < start:
        return None
    months = (end_d.year - start.year) * 12 + (end_d.month - start.month)
    if end_d.day < start.day:
        months -= 1
    years, rem = divmod(max(0, months), 12)
    parts: list[str] = []
    if years:
        parts.append(f"{years} año{'s' if years != 1 else ''}")
    if rem:
        parts.append(f"{rem} mes{'es' if rem != 1 else ''}")
    return ", ".join(parts) if parts else "Menos de 1 mes"


def education_read(row: EmployeeEducation) -> EmployeeEducationRead:
    return EmployeeEducationRead(
        id=row.id,
        education_level=row.education_level,  # type: ignore[arg-type]
        institution=row.institution,
        program=row.program,
        graduation_year=row.graduation_year,
        status=row.status,  # type: ignore[arg-type]
        certificate_url=row.certificate_url,
    )


def training_read(row: EmployeeTraining) -> EmployeeTrainingRead:
    return EmployeeTrainingRead(
        id=row.id,
        name=row.name,
        provider=row.provider,
        completed_at=row.completed_at,
        hours=row.hours,
        training_type=row.training_type,  # type: ignore[arg-type]
        certificate_url=row.certificate_url,
    )


def prior_job_read(row: EmployeePriorJob) -> EmployeePriorJobRead:
    return EmployeePriorJobRead(
        id=row.id,
        company_name=row.company_name,
        position=row.position,
        start_date=row.start_date,
        end_date=row.end_date,
        duration_text=calc_job_duration(row.start_date, row.end_date),
        economic_sector=row.economic_sector,
        leave_reason=row.leave_reason,
        reference_phone=row.reference_phone,
    )


def _money(val: Decimal | float | int | None) -> float | None:
    if val is None:
        return None
    return float(val)


def language_read(row: EmployeeLanguage) -> EmployeeLanguageRead:
    return EmployeeLanguageRead(
        id=row.id,
        language=row.language,
        level=row.level,  # type: ignore[arg-type]
    )


def software_skill_read(row: EmployeeSoftwareSkill) -> EmployeeSoftwareSkillRead:
    return EmployeeSoftwareSkillRead(
        id=row.id,
        name=row.name,
        proficiency=row.proficiency,  # type: ignore[arg-type]
    )


def driving_license_read(row: EmployeeDrivingLicense) -> EmployeeDrivingLicenseRead:
    return EmployeeDrivingLicenseRead(
        id=row.id,
        category=row.category,
        expires_at=row.expires_at,
    )


def work_sst_cert_read(row: EmployeeWorkSstCert) -> EmployeeWorkSstCertRead:
    return EmployeeWorkSstCertRead(
        id=row.id,
        cert_type=row.cert_type,  # type: ignore[arg-type]
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        certificate_url=row.certificate_url,
    )


def competency_evaluation_read(row: EmployeeCompetencyEvaluation) -> EmployeeCompetencyEvaluationRead:
    return EmployeeCompetencyEvaluationRead(
        id=row.id,
        period_label=row.period_label,
        rating=row.rating,
        evaluator_name=row.evaluator_name,
        notes=row.notes,
    )


def sst_profile_read(row: EmployeeSstProfile | None) -> EmployeeSstProfileRead:
    if row is None:
        return EmployeeSstProfileRead()
    return EmployeeSstProfileRead(
        entry_exam_date=row.entry_exam_date,
        entry_medical_concept=row.entry_medical_concept,
        entry_restrictions=row.entry_restrictions,
        occupational_disease=row.occupational_disease,
        current_medical_restrictions=row.current_medical_restrictions,
    )


def sst_periodic_exam_read(row: EmployeeSstPeriodicExam) -> EmployeeSstPeriodicExamRead:
    return EmployeeSstPeriodicExamRead(
        id=row.id,
        exam_date=row.exam_date,
        result=row.result,
        notes=row.notes,
    )


def sst_incapacity_read(row: EmployeeSstIncapacity) -> EmployeeSstIncapacityRead:
    return EmployeeSstIncapacityRead(
        id=row.id,
        origin=row.origin,  # type: ignore[arg-type]
        diagnosis=row.diagnosis,
        days=row.days,
        start_date=row.start_date,
        end_date=row.end_date,
    )


def sst_accident_read(row: EmployeeSstAccident) -> EmployeeSstAccidentRead:
    return EmployeeSstAccidentRead(
        id=row.id,
        occurred_at=row.occurred_at,
        description=row.description,
        lost_days=row.lost_days,
    )


def sst_ppe_read(row: EmployeeSstPpe) -> EmployeeSstPpeRead:
    return EmployeeSstPpeRead(
        id=row.id,
        item_name=row.item_name,
        delivered_at=row.delivered_at,
        receipt_signed=row.receipt_signed,
    )


def contract_history_read(row: EmployeeContractHistory) -> EmployeeContractHistoryRead:
    return EmployeeContractHistoryRead(
        id=row.id,
        effective_date=row.effective_date,
        contract_type=row.contract_type,
        end_date=row.end_date,
        notes=row.notes,
    )


def salary_history_read(row: EmployeeSalaryHistory) -> EmployeeSalaryHistoryRead:
    return EmployeeSalaryHistoryRead(
        id=row.id,
        effective_date=row.effective_date,
        previous_salary=_money(row.previous_salary),
        new_salary=_money(row.new_salary),
        reason=row.reason,
    )


def performance_review_read(row: EmployeePerformanceReview) -> EmployeePerformanceReviewRead:
    return EmployeePerformanceReviewRead(
        id=row.id,
        period_label=row.period_label,
        rating=row.rating,
        evaluator_name=row.evaluator_name,
        notes=row.notes,
    )


def recognition_read(row: EmployeeRecognition) -> EmployeeRecognitionRead:
    return EmployeeRecognitionRead(
        id=row.id,
        title=row.title,
        recognized_at=row.recognized_at,
        description=row.description,
    )


def disciplinary_action_read(row: EmployeeDisciplinaryAction) -> EmployeeDisciplinaryActionRead:
    return EmployeeDisciplinaryActionRead(
        id=row.id,
        action_type=row.action_type,  # type: ignore[arg-type]
        occurred_at=row.occurred_at,
        description=row.description,
    )


def absence_record_read(row: EmployeeAbsenceRecord) -> EmployeeAbsenceRecordRead:
    return EmployeeAbsenceRecordRead(
        id=row.id,
        absence_type=row.absence_type,  # type: ignore[arg-type]
        start_date=row.start_date,
        end_date=row.end_date,
        days=row.days,
        notes=row.notes,
    )

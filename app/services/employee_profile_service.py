"""Expediente HR: acceso (fase 0) y datos personales/laborales (fase 1)."""

from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from decimal import Decimal

from app.models.employee_career import EmployeeEducation, EmployeePriorJob, EmployeeTraining
from app.models.employee_custom import EmployeeCustomFieldValue, EmployeePayrollEntry
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
from app.models.user import User
from app.schemas.employee import EmployeeProfileAccessRead
from app.schemas.employee_profile import (
    EmployeeDependentWrite,
    EmployeeAbsenceRecordWrite,
    EmployeeCompetencyEvaluationWrite,
    EmployeeContractHistoryWrite,
    EmployeeDisciplinaryActionWrite,
    EmployeeDrivingLicenseWrite,
    EmployeeEducationWrite,
    EmployeeLaborUpdate,
    EmployeeLanguageWrite,
    EmployeePerformanceReviewWrite,
    EmployeePersonalUpdate,
    EmployeePriorJobWrite,
    EmployeeProfileFullRead,
    EmployeeProfilePatch,
    EmployeeProfileSummaryRead,
    EmployeeRecognitionWrite,
    EmployeeSalaryHistoryWrite,
    EmployeeSoftwareSkillWrite,
    EmployeeSstAccidentWrite,
    EmployeeSstIncapacityWrite,
    EmployeeSstPeriodicExamWrite,
    EmployeeSstPpeWrite,
    EmployeeSstProfileUpdate,
    EmployeeTrainingWrite,
    EmployeeWorkSstCertWrite,
)
from app.services.employee_profile_mappers import (
    absence_record_read,
    competency_evaluation_read,
    contract_history_read,
    dependent_read,
    disciplinary_action_read,
    document_read,
    driving_license_read,
    education_read,
    language_read,
    labor_read,
    performance_review_read,
    personal_read,
    prior_job_read,
    recognition_read,
    salary_history_read,
    software_skill_read,
    sst_accident_read,
    sst_incapacity_read,
    sst_periodic_exam_read,
    sst_ppe_read,
    sst_profile_read,
    training_read,
    work_sst_cert_read,
)
from app.core.name_parts import split_full_name
from app.services.employee_service import ensure_employee_access, get_employee
from app.services.rbac_service import user_has_any_permission

PERM_PROFILE_FULL = "employees.profile.full"
PERM_PROFILE_EDIT = "employees.profile.edit"
PERM_PROFILE_EXPORT = "employees.profile.export"
PERM_PROFILE_ALERTS = "employees.profile.alerts"
PERM_CUSTOM_MANAGE = "employees.profile.custom_fields.manage"
PERM_PAYROLL = "employees.profile.payroll"

_PERSONAL_TRACKED = (
    "first_name",
    "second_name",
    "first_surname",
    "second_surname",
    "document_type",
    "birth_date",
    "gender",
    "marital_status",
    "children_count",
    "residence_city",
    "residence_address",
    "neighborhood",
    "phone",
    "personal_email",
    "corporate_email",
    "blood_type",
    "rh_factor",
)

_LABOR_TRACKED = (
    "linkage_type",
    "temp_agency_name",
    "work_site_city",
    "hierarchical_level",
    "hire_date",
    "contract_type",
    "contract_end_date",
    "base_salary",
    "work_schedule_type",
    "work_modality",
    "eps_affiliation_number",
    "eps_name",
    "pension_fund",
    "severance_fund",
    "family_compensation_box",
    "arl_name",
    "arl_risk_level",
    "bank_name",
    "bank_account_type",
    "bank_account_number",
    "collaborator_status",
)


async def user_can_view_full_profile(db: AsyncSession, user: User) -> bool:
    return await user_has_any_permission(db, user, PERM_PROFILE_FULL)


async def user_can_edit_profile(db: AsyncSession, user: User) -> bool:
    return await user_has_any_permission(db, user, PERM_PROFILE_EDIT)


async def resolve_profile_access(
    db: AsyncSession,
    actor: User,
    emp: Employee,
) -> EmployeeProfileAccessRead:
    ensure_employee_access(actor, emp)
    full = await user_can_view_full_profile(db, actor)
    return EmployeeProfileAccessRead(
        employee_id=emp.id,
        view_level="full" if full else "basic",
        can_edit_profile=await user_can_edit_profile(db, actor) if full else False,
        can_export=await user_has_any_permission(db, actor, PERM_PROFILE_EXPORT) if full else False,
        can_see_alerts=await user_has_any_permission(db, actor, PERM_PROFILE_ALERTS) if full else False,
        expediente_available=full,
    )


def _full_name_from_parts(
    first: str | None,
    second: str | None,
    sur1: str | None,
    sur2: str | None,
) -> str | None:
    bits = [b.strip() for b in (first, second, sur1, sur2) if b and b.strip()]
    return " ".join(bits).upper() if bits else None


async def _load_employee_profile(db: AsyncSession, employee_id: int) -> Employee | None:
    r = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.area),
            selectinload(Employee.temporal_category),
            selectinload(Employee.leader_user),
            selectinload(Employee.personal),
            selectinload(Employee.labor),
            selectinload(Employee.dependents),
            selectinload(Employee.documents).selectinload(EmployeeDocument.uploaded_by),
            selectinload(Employee.education_records),
            selectinload(Employee.training_records),
            selectinload(Employee.prior_jobs),
            selectinload(Employee.languages),
            selectinload(Employee.software_skills),
            selectinload(Employee.driving_licenses),
            selectinload(Employee.work_sst_certs),
            selectinload(Employee.competency_evaluations),
            selectinload(Employee.sst_profile),
            selectinload(Employee.sst_periodic_exams),
            selectinload(Employee.sst_incapacities),
            selectinload(Employee.sst_accidents),
            selectinload(Employee.sst_ppe),
            selectinload(Employee.contract_history),
            selectinload(Employee.salary_history),
            selectinload(Employee.performance_reviews),
            selectinload(Employee.recognitions),
            selectinload(Employee.disciplinary_actions),
            selectinload(Employee.absence_records),
            selectinload(Employee.custom_field_values).selectinload(
                EmployeeCustomFieldValue.field_def
            ),
            selectinload(Employee.payroll_entries).selectinload(EmployeePayrollEntry.created_by),
        )
        .where(Employee.id == employee_id)
    )
    return r.scalar_one_or_none()


async def _ensure_personal(db: AsyncSession, emp: Employee) -> EmployeePersonal:
    if emp.personal is None:
        row = EmployeePersonal(employee_id=emp.id)
        db.add(row)
        await db.flush()
        emp.personal = row
    return emp.personal


async def _ensure_labor(db: AsyncSession, emp: Employee) -> EmployeeLabor:
    if emp.labor is None:
        row = EmployeeLabor(employee_id=emp.id)
        db.add(row)
        await db.flush()
        emp.labor = row
    return emp.labor


def _completeness_percent(
    emp: Employee,
    personal: EmployeePersonal | None,
    labor: EmployeeLabor | None,
    dependents: list[EmployeeDependent],
    documents: list[EmployeeDocument] | None = None,
    education: list[EmployeeEducation] | None = None,
    training: list[EmployeeTraining] | None = None,
    prior_jobs: list[EmployeePriorJob] | None = None,
    languages: list[EmployeeLanguage] | None = None,
    sst_profile: EmployeeSstProfile | None = None,
) -> int:
    filled = 0
    total = 0

    def check(val: Any) -> None:
        nonlocal filled, total
        total += 1
        if val is not None and str(val).strip() != "":
            filled += 1

    check(emp.name)
    check(emp.identification_number)
    check(emp.position)
    check(emp.area_id)
    if personal:
        for field in _PERSONAL_TRACKED:
            check(getattr(personal, field, None))
    else:
        total += len(_PERSONAL_TRACKED)
    if labor:
        for field in _LABOR_TRACKED:
            check(getattr(labor, field, None))
    else:
        total += len(_LABOR_TRACKED)
    if personal and personal.children_count and personal.children_count > 0:
        total += 1
        if dependents:
            filled += 1
    total += 3
    docs = documents or []
    if docs:
        filled += min(3, len(docs))
    if education:
        filled += min(2, len(education))
    else:
        total += 2
    if training:
        filled += min(2, len(training))
    else:
        total += 2
    if prior_jobs:
        filled += min(1, len(prior_jobs))
    else:
        total += 1
    total += 1
    if languages:
        filled += 1
    if sst_profile and sst_profile.entry_exam_date:
        filled += 1

    if total == 0:
        return 0
    return min(100, round(100 * filled / total))


async def _build_profile_read(
    db: AsyncSession,
    actor: User,
    emp: Employee,
    *,
    can_edit: bool,
) -> EmployeeProfileFullRead:
    from app.services.employee_custom_field_service import (
        merge_custom_fields_read,
        user_can_manage_custom_fields,
    )
    from app.services.employee_payroll_service import (
        payroll_entry_read,
        payroll_summary_from_employee,
        user_can_edit_payroll,
    )

    custom = await merge_custom_fields_read(db, emp)
    payroll_sum = payroll_summary_from_employee(emp)
    payroll_list = [
        payroll_entry_read(e)
        for e in sorted(
            emp.payroll_entries or [],
            key=lambda x: (x.period_month, x.id),
            reverse=True,
        )
    ]
    can_manage_cf = await user_can_manage_custom_fields(db, actor)
    can_payroll = await user_can_edit_payroll(db, actor)
    personal = emp.personal
    labor = emp.labor
    deps = list(emp.dependents or [])
    docs = sorted(emp.documents or [], key=lambda d: d.created_at, reverse=True)
    edu = list(emp.education_records or [])
    trn = list(emp.training_records or [])
    jobs = list(emp.prior_jobs or [])
    langs = list(emp.languages or [])
    return EmployeeProfileFullRead(
        employee=_summary(emp),
        personal=personal_read(personal),
        labor=labor_read(labor),
        dependents=[dependent_read(d) for d in deps],
        documents=[document_read(d) for d in docs],
        education=[education_read(e) for e in edu],
        training=[training_read(t) for t in trn],
        prior_jobs=[prior_job_read(j) for j in jobs],
        languages=[language_read(x) for x in langs],
        software_skills=[software_skill_read(x) for x in (emp.software_skills or [])],
        driving_licenses=[driving_license_read(x) for x in (emp.driving_licenses or [])],
        work_sst_certs=[work_sst_cert_read(x) for x in (emp.work_sst_certs or [])],
        competency_evaluations=[
            competency_evaluation_read(x) for x in (emp.competency_evaluations or [])
        ],
        sst_profile=sst_profile_read(emp.sst_profile),
        sst_periodic_exams=[sst_periodic_exam_read(x) for x in (emp.sst_periodic_exams or [])],
        sst_incapacities=[sst_incapacity_read(x) for x in (emp.sst_incapacities or [])],
        sst_accidents=[sst_accident_read(x) for x in (emp.sst_accidents or [])],
        sst_ppe=[sst_ppe_read(x) for x in (emp.sst_ppe or [])],
        contract_history=[contract_history_read(x) for x in (emp.contract_history or [])],
        salary_history=[salary_history_read(x) for x in (emp.salary_history or [])],
        performance_reviews=[performance_review_read(x) for x in (emp.performance_reviews or [])],
        recognitions=[recognition_read(x) for x in (emp.recognitions or [])],
        disciplinary_actions=[
            disciplinary_action_read(x) for x in (emp.disciplinary_actions or [])
        ],
        absence_records=[absence_record_read(x) for x in (emp.absence_records or [])],
        custom_fields=custom,
        payroll_summary=payroll_sum,
        payroll_entries=payroll_list,
        completeness_percent=_completeness_percent(
            emp, personal, labor, deps, docs, edu, trn, jobs, langs, emp.sst_profile
        ),
        can_edit=can_edit,
        can_edit_documents=can_edit,
        can_manage_custom_fields=can_manage_cf,
        can_edit_payroll=can_payroll,
    )


def _summary(emp: Employee) -> EmployeeProfileSummaryRead:
    temporal_name = (
        emp.temporal_category.name if emp.temporal_category is not None else ""
    )
    return EmployeeProfileSummaryRead(
        id=emp.id,
        name=emp.name,
        identification_number=emp.identification_number,
        position=emp.position,
        area_id=emp.area_id,
        area_name=emp.area.name if emp.area else "",
        temporal_category_name=temporal_name,
        leader_id=emp.leader_id,
        leader_name=emp.leader_user.name if emp.leader_user else None,
        status=emp.status,
        updated_at=emp.updated_at,
    )


def _has_personal_name_parts(personal: EmployeePersonal) -> bool:
    return bool(
        (personal.first_name and personal.first_name.strip())
        or (personal.first_surname and personal.first_surname.strip())
    )


async def _autofill_profile_from_employee(db: AsyncSession, emp: Employee) -> bool:
    """Completa expediente con datos del registro base si aún están vacíos."""
    changed = False
    personal = await _ensure_personal(db, emp)
    if not _has_personal_name_parts(personal) and emp.name.strip():
        fn, sn, fs, ss = split_full_name(emp.name)
        if fn and not personal.first_name:
            personal.first_name = fn
            changed = True
        if sn and not personal.second_name:
            personal.second_name = sn
            changed = True
        if fs and not personal.first_surname:
            personal.first_surname = fs
            changed = True
        if ss and not personal.second_surname:
            personal.second_surname = ss
            changed = True
    if not personal.document_type:
        personal.document_type = "CC"
        changed = True

    labor = await _ensure_labor(db, emp)
    temporal_name = (
        emp.temporal_category.name if emp.temporal_category is not None else ""
    )
    if temporal_name and not (labor.temp_agency_name or "").strip():
        labor.temp_agency_name = temporal_name
        changed = True
    if emp.temporal_category_id and not labor.linkage_type:
        labor.linkage_type = "temp_agency"
        changed = True
    elif not emp.temporal_category_id and not labor.linkage_type:
        labor.linkage_type = "direct"
        changed = True
    if not labor.collaborator_status:
        status_map = {
            "active": "activo",
            "inactive": "retirado",
        }
        mapped = status_map.get(emp.status)
        if mapped:
            labor.collaborator_status = mapped
            changed = True
    if not (labor.hierarchical_level or "").strip() and emp.position.strip():
        pos = emp.position.lower()
        if "gerente" in pos or "gerencia" in pos:
            labor.hierarchical_level = "gerencia"
            changed = True
        elif "director" in pos:
            labor.hierarchical_level = "director"
            changed = True
        elif "jefe" in pos:
            labor.hierarchical_level = "jefe"
            changed = True
        elif "coordinador" in pos:
            labor.hierarchical_level = "coordinador"
            changed = True
        elif "técnico" in pos or "tecnico" in pos:
            labor.hierarchical_level = "tecnico"
            changed = True
        elif "operario" in pos or "operador" in pos:
            labor.hierarchical_level = "operario"
            changed = True

    if changed:
        await db.flush()
    return changed


async def get_full_profile(
    db: AsyncSession,
    actor: User,
    employee_id: int,
) -> EmployeeProfileFullRead:
    if not await user_can_view_full_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para ver el expediente completo")
    emp = await _load_employee_profile(db, employee_id)
    if not emp:
        from app.core.exceptions import not_found

        raise not_found()
    ensure_employee_access(actor, emp)
    if await _autofill_profile_from_employee(db, emp):
        await db.commit()
        emp = await _load_employee_profile(db, employee_id)
        assert emp is not None
    can_edit = await user_can_edit_profile(db, actor)
    return await _build_profile_read(db, actor, emp, can_edit=can_edit)


async def upload_profile_photo(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    upload: UploadFile,
) -> EmployeeProfileFullRead:
    from app.core.file_upload import save_profile_photo_file

    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para editar el expediente")
    emp = await _load_employee_profile(db, employee_id)
    if not emp:
        from app.core.exceptions import not_found

        raise not_found()
    ensure_employee_access(actor, emp)
    personal = await _ensure_personal(db, emp)
    url, _, _ = await save_profile_photo_file(upload, employee_id)
    personal.photo_url = url
    await db.commit()
    emp = await _load_employee_profile(db, employee_id)
    assert emp is not None
    return await _build_profile_read(db, actor, emp, can_edit=True)


def _apply_patch_fields(row: Any, data: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if field in data:
            setattr(row, field, data[field])


async def _sync_dependents(
    db: AsyncSession,
    emp: Employee,
    items: list[EmployeeDependentWrite] | None,
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeDependent).where(EmployeeDependent.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeDependent(
                employee_id=emp.id,
                full_name=item.full_name.strip(),
                parentesco=item.relationship,
                birth_date=item.birth_date,
                schooling=item.schooling,
            )
        )
    await db.flush()


async def _sync_education(
    db: AsyncSession,
    emp: Employee,
    items: list[EmployeeEducationWrite] | None,
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeEducation).where(EmployeeEducation.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeEducation(
                employee_id=emp.id,
                education_level=item.education_level,
                institution=item.institution,
                program=item.program,
                graduation_year=item.graduation_year,
                status=item.status,
                certificate_url=item.certificate_url,
            )
        )
    await db.flush()


async def _sync_training(
    db: AsyncSession,
    emp: Employee,
    items: list[EmployeeTrainingWrite] | None,
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeTraining).where(EmployeeTraining.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeTraining(
                employee_id=emp.id,
                name=item.name.strip(),
                provider=item.provider,
                completed_at=item.completed_at,
                hours=item.hours,
                training_type=item.training_type,
                certificate_url=item.certificate_url,
            )
        )
    await db.flush()


async def _sync_prior_jobs(
    db: AsyncSession,
    emp: Employee,
    items: list[EmployeePriorJobWrite] | None,
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeePriorJob).where(EmployeePriorJob.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeePriorJob(
                employee_id=emp.id,
                company_name=item.company_name.strip(),
                position=item.position,
                start_date=item.start_date,
                end_date=item.end_date,
                economic_sector=item.economic_sector,
                leave_reason=item.leave_reason,
                reference_phone=item.reference_phone,
            )
        )
    await db.flush()


async def _ensure_sst_profile(db: AsyncSession, emp: Employee) -> EmployeeSstProfile:
    if emp.sst_profile is None:
        row = EmployeeSstProfile(employee_id=emp.id)
        db.add(row)
        await db.flush()
        emp.sst_profile = row
    return emp.sst_profile


def _to_decimal(val: float | None) -> Decimal | None:
    if val is None:
        return None
    return Decimal(str(val))


async def _sync_languages(
    db: AsyncSession, emp: Employee, items: list[EmployeeLanguageWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeLanguage).where(EmployeeLanguage.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeLanguage(
                employee_id=emp.id,
                language=item.language.strip(),
                level=item.level,
            )
        )
    await db.flush()


async def _sync_software_skills(
    db: AsyncSession, emp: Employee, items: list[EmployeeSoftwareSkillWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeSoftwareSkill).where(EmployeeSoftwareSkill.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeSoftwareSkill(
                employee_id=emp.id,
                name=item.name.strip(),
                proficiency=item.proficiency,
            )
        )
    await db.flush()


async def _sync_driving_licenses(
    db: AsyncSession, emp: Employee, items: list[EmployeeDrivingLicenseWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeDrivingLicense).where(EmployeeDrivingLicense.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeDrivingLicense(
                employee_id=emp.id,
                category=item.category.strip().upper(),
                expires_at=item.expires_at,
            )
        )
    await db.flush()


async def _sync_work_sst_certs(
    db: AsyncSession, emp: Employee, items: list[EmployeeWorkSstCertWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeWorkSstCert).where(EmployeeWorkSstCert.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeWorkSstCert(
                employee_id=emp.id,
                cert_type=item.cert_type,
                issued_at=item.issued_at,
                expires_at=item.expires_at,
                certificate_url=item.certificate_url,
            )
        )
    await db.flush()


async def _sync_competency_evaluations(
    db: AsyncSession, emp: Employee, items: list[EmployeeCompetencyEvaluationWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(
        delete(EmployeeCompetencyEvaluation).where(EmployeeCompetencyEvaluation.employee_id == emp.id)
    )
    for item in items:
        db.add(
            EmployeeCompetencyEvaluation(
                employee_id=emp.id,
                period_label=item.period_label.strip(),
                rating=item.rating,
                evaluator_name=item.evaluator_name,
                notes=item.notes,
            )
        )
    await db.flush()


async def _apply_sst_profile(
    db: AsyncSession, emp: Employee, data: EmployeeSstProfileUpdate | None
) -> None:
    if data is None:
        return
    row = await _ensure_sst_profile(db, emp)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(row, field, val)
    await db.flush()


async def _sync_sst_periodic_exams(
    db: AsyncSession, emp: Employee, items: list[EmployeeSstPeriodicExamWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(
        delete(EmployeeSstPeriodicExam).where(EmployeeSstPeriodicExam.employee_id == emp.id)
    )
    for item in items:
        db.add(
            EmployeeSstPeriodicExam(
                employee_id=emp.id,
                exam_date=item.exam_date,
                result=item.result,
                notes=item.notes,
            )
        )
    await db.flush()


async def _sync_sst_incapacities(
    db: AsyncSession, emp: Employee, items: list[EmployeeSstIncapacityWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(
        delete(EmployeeSstIncapacity).where(EmployeeSstIncapacity.employee_id == emp.id)
    )
    for item in items:
        db.add(
            EmployeeSstIncapacity(
                employee_id=emp.id,
                origin=item.origin,
                diagnosis=item.diagnosis,
                days=item.days,
                start_date=item.start_date,
                end_date=item.end_date,
            )
        )
    await db.flush()


async def _sync_sst_accidents(
    db: AsyncSession, emp: Employee, items: list[EmployeeSstAccidentWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeSstAccident).where(EmployeeSstAccident.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeSstAccident(
                employee_id=emp.id,
                occurred_at=item.occurred_at,
                description=item.description,
                lost_days=item.lost_days,
            )
        )
    await db.flush()


async def _sync_sst_ppe(
    db: AsyncSession, emp: Employee, items: list[EmployeeSstPpeWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeSstPpe).where(EmployeeSstPpe.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeSstPpe(
                employee_id=emp.id,
                item_name=item.item_name.strip(),
                delivered_at=item.delivered_at,
                receipt_signed=item.receipt_signed,
            )
        )
    await db.flush()


async def _sync_contract_history(
    db: AsyncSession, emp: Employee, items: list[EmployeeContractHistoryWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(
        delete(EmployeeContractHistory).where(EmployeeContractHistory.employee_id == emp.id)
    )
    for item in items:
        db.add(
            EmployeeContractHistory(
                employee_id=emp.id,
                effective_date=item.effective_date,
                contract_type=item.contract_type,
                end_date=item.end_date,
                notes=item.notes,
            )
        )
    await db.flush()


async def _sync_salary_history(
    db: AsyncSession, emp: Employee, items: list[EmployeeSalaryHistoryWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeSalaryHistory).where(EmployeeSalaryHistory.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeSalaryHistory(
                employee_id=emp.id,
                effective_date=item.effective_date,
                previous_salary=_to_decimal(item.previous_salary),
                new_salary=_to_decimal(item.new_salary),
                reason=item.reason,
            )
        )
    await db.flush()


async def _sync_performance_reviews(
    db: AsyncSession, emp: Employee, items: list[EmployeePerformanceReviewWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(
        delete(EmployeePerformanceReview).where(EmployeePerformanceReview.employee_id == emp.id)
    )
    for item in items:
        db.add(
            EmployeePerformanceReview(
                employee_id=emp.id,
                period_label=item.period_label.strip(),
                rating=item.rating,
                evaluator_name=item.evaluator_name,
                notes=item.notes,
            )
        )
    await db.flush()


async def _sync_recognitions(
    db: AsyncSession, emp: Employee, items: list[EmployeeRecognitionWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeRecognition).where(EmployeeRecognition.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeRecognition(
                employee_id=emp.id,
                title=item.title.strip(),
                recognized_at=item.recognized_at,
                description=item.description,
            )
        )
    await db.flush()


async def _sync_disciplinary_actions(
    db: AsyncSession, emp: Employee, items: list[EmployeeDisciplinaryActionWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(
        delete(EmployeeDisciplinaryAction).where(EmployeeDisciplinaryAction.employee_id == emp.id)
    )
    for item in items:
        db.add(
            EmployeeDisciplinaryAction(
                employee_id=emp.id,
                action_type=item.action_type,
                occurred_at=item.occurred_at,
                description=item.description,
            )
        )
    await db.flush()


async def _sync_absence_records(
    db: AsyncSession, emp: Employee, items: list[EmployeeAbsenceRecordWrite] | None
) -> None:
    if items is None:
        return
    await db.execute(delete(EmployeeAbsenceRecord).where(EmployeeAbsenceRecord.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeeAbsenceRecord(
                employee_id=emp.id,
                absence_type=item.absence_type,
                start_date=item.start_date,
                end_date=item.end_date,
                days=item.days,
                notes=item.notes,
            )
        )
    await db.flush()


async def update_profile(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    body: EmployeeProfilePatch,
) -> EmployeeProfileFullRead:
    if not await user_can_edit_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para editar el expediente")
    emp = await _load_employee_profile(db, employee_id)
    if not emp:
        from app.core.exceptions import not_found

        raise not_found()
    ensure_employee_access(actor, emp)

    if body.personal is not None:
        personal = await _ensure_personal(db, emp)
        pdata = body.personal.model_dump(exclude_unset=True, exclude={"dependents"})
        _apply_patch_fields(personal, pdata, _PERSONAL_TRACKED)
        await _sync_dependents(db, emp, body.personal.dependents)
        full_name = _full_name_from_parts(
            personal.first_name,
            personal.second_name,
            personal.first_surname,
            personal.second_surname,
        )
        if full_name:
            emp.name = full_name

    if body.labor is not None:
        labor = await _ensure_labor(db, emp)
        ldata = body.labor.model_dump(exclude_unset=True)
        _apply_patch_fields(labor, ldata, _LABOR_TRACKED + ("notes",))

    await _sync_education(db, emp, body.education)
    await _sync_training(db, emp, body.training)
    await _sync_prior_jobs(db, emp, body.prior_jobs)
    await _sync_languages(db, emp, body.languages)
    await _sync_software_skills(db, emp, body.software_skills)
    await _sync_driving_licenses(db, emp, body.driving_licenses)
    await _sync_work_sst_certs(db, emp, body.work_sst_certs)
    await _sync_competency_evaluations(db, emp, body.competency_evaluations)
    await _apply_sst_profile(db, emp, body.sst_profile)
    await _sync_sst_periodic_exams(db, emp, body.sst_periodic_exams)
    await _sync_sst_incapacities(db, emp, body.sst_incapacities)
    await _sync_sst_accidents(db, emp, body.sst_accidents)
    await _sync_sst_ppe(db, emp, body.sst_ppe)
    await _sync_contract_history(db, emp, body.contract_history)
    await _sync_salary_history(db, emp, body.salary_history)
    await _sync_performance_reviews(db, emp, body.performance_reviews)
    await _sync_recognitions(db, emp, body.recognitions)
    await _sync_disciplinary_actions(db, emp, body.disciplinary_actions)
    await _sync_absence_records(db, emp, body.absence_records)

    from app.services.employee_custom_field_service import sync_custom_field_values
    from app.services.employee_payroll_service import _sync_payroll_entries

    await sync_custom_field_values(db, emp, body.custom_fields)
    await _sync_payroll_entries(db, emp, actor, body.payroll_entries)

    await db.commit()
    emp = await _load_employee_profile(db, employee_id)
    assert emp is not None
    return await _build_profile_read(db, actor, emp, can_edit=True)

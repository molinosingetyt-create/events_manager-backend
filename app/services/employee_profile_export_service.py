"""Exportación resumida del expediente HR (Excel)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.employee_profile import EmployeeLabor
from app.models.enums import EntityStatus
from app.models.user import User
from app.schemas.employee_profile_phase5 import (
    EmployeeProfileExportListRead,
    EmployeeProfileExportRowRead,
)
from app.services.employee_profile_alerts_service import compute_employee_alerts
from app.services.employee_profile_service import (
    PERM_PROFILE_EXPORT,
    _completeness_percent,
    _load_employee_profile,
    user_can_view_full_profile,
)
from app.services.employee_service import ensure_employee_access, acts_as_team_leader
from app.services.rbac_service import user_has_any_permission


async def _load_employees_for_export(db: AsyncSession, actor: User) -> list[Employee]:
    q = (
        select(Employee)
        .outerjoin(EmployeeLabor, EmployeeLabor.employee_id == Employee.id)
        .options(
            selectinload(Employee.area),
            selectinload(Employee.leader_user),
            selectinload(Employee.personal),
            selectinload(Employee.labor),
            selectinload(Employee.dependents),
            selectinload(Employee.documents),
            selectinload(Employee.education_records),
            selectinload(Employee.training_records),
            selectinload(Employee.prior_jobs),
            selectinload(Employee.languages),
            selectinload(Employee.driving_licenses),
            selectinload(Employee.work_sst_certs),
            selectinload(Employee.sst_profile),
            selectinload(Employee.sst_periodic_exams),
        )
        .order_by(Employee.name)
    )
    if acts_as_team_leader(actor):
        q = q.where(Employee.leader_id == actor.id)
    r = await db.execute(q)
    return list(r.scalars().unique().all())


def _row_from_employee(emp: Employee) -> EmployeeProfileExportRowRead:
    labor = emp.labor
    personal = emp.personal
    alerts = compute_employee_alerts(emp)
    completeness = _completeness_percent(
        emp,
        personal,
        labor,
        list(emp.dependents or []),
        list(emp.documents or []),
        list(emp.education_records or []),
        list(emp.training_records or []),
        list(emp.prior_jobs or []),
        list(emp.languages or []),
        emp.sst_profile,
    )
    return EmployeeProfileExportRowRead(
        employee_id=emp.id,
        identification_number=emp.identification_number,
        name=emp.name,
        position=emp.position,
        area_name=emp.area.name if emp.area else "",
        leader_name=emp.leader_user.name if emp.leader_user else None,
        status=emp.status,
        work_site_city=labor.work_site_city if labor else None,
        contract_type=labor.contract_type if labor else None,
        contract_end_date=labor.contract_end_date if labor else None,
        hire_date=labor.hire_date if labor else None,
        collaborator_status=labor.collaborator_status if labor else None,
        phone=personal.phone if personal else None,
        corporate_email=personal.corporate_email if personal else None,
        personal_email=personal.personal_email if personal else None,
        completeness_percent=completeness,
        active_alerts_count=len(alerts),
        documents_count=len(emp.documents or []),
        education_count=len(emp.education_records or []),
        training_count=len(emp.training_records or []),
    )


async def export_profile_summary(
    db: AsyncSession,
    actor: User,
    *,
    active_only: bool = True,
) -> EmployeeProfileExportListRead:
    if not await user_has_any_permission(db, actor, PERM_PROFILE_EXPORT):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para exportar expedientes")
    if not await user_can_view_full_profile(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para ver el expediente completo")
    employees = await _load_employees_for_export(db, actor)
    rows: list[EmployeeProfileExportRowRead] = []
    for emp in employees:
        ensure_employee_access(actor, emp)
        if active_only and emp.status != EntityStatus.ACTIVE.value:
            continue
        rows.append(_row_from_employee(emp))
    return EmployeeProfileExportListRead(rows=rows, generated_at=date.today())


async def export_single_profile_row(
    db: AsyncSession,
    actor: User,
    employee_id: int,
) -> EmployeeProfileExportRowRead:
    if not await user_has_any_permission(db, actor, PERM_PROFILE_EXPORT):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para exportar expedientes")
    emp = await _load_employee_profile(db, employee_id)
    if not emp:
        from app.core.exceptions import not_found

        raise not_found()
    ensure_employee_access(actor, emp)
    return _row_from_employee(emp)

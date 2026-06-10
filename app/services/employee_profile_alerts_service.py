"""Alertas automáticas del expediente HR."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.enums import EntityStatus
from app.schemas.employee_profile_phase5 import (
    EmployeeProfileAlertRead,
    EmployeeProfileAlertsBundleRead,
    EmployeeProfileAlertsListRead,
)
from app.services.employee_profile_mappers import effective_document_status
from app.services.employee_profile_service import (
    PERM_PROFILE_ALERTS,
    _completeness_percent,
    _load_employee_profile,
    user_can_view_full_profile,
)
from app.services.employee_service import ensure_employee_access, acts_as_team_leader
from app.services.rbac_service import user_has_any_permission
from app.models.user import User

ALERT_HORIZON_DAYS = 60
BIRTHDAY_HORIZON_DAYS = 14
PERIODIC_EXAM_MONTHS = 12

_REQUIRED_DOC_KINDS = frozenset({"cedula", "hoja_vida", "examen_ingreso", "contrato"})


def _days_until(target: date, today: date) -> int:
    return (target - today).days


def _next_birthday(birth: date, today: date) -> date:
    candidate = birth.replace(year=today.year)
    if candidate < today:
        candidate = candidate.replace(year=today.year + 1)
    return candidate


def compute_employee_alerts(emp: Employee, today: date | None = None) -> list[EmployeeProfileAlertRead]:
    today = today or date.today()
    horizon = today + timedelta(days=ALERT_HORIZON_DAYS)
    alerts: list[EmployeeProfileAlertRead] = []

    if emp.status != EntityStatus.ACTIVE.value:
        return alerts

    labor = emp.labor
    personal = emp.personal

    if labor and labor.contract_end_date:
        end = labor.contract_end_date
        if end < today:
            alerts.append(
                EmployeeProfileAlertRead(
                    code="contract_expired",
                    severity="critical",
                    title="Contrato vencido",
                    message=f"El contrato venció el {end.isoformat()}.",
                    due_date=end,
                )
            )
        elif end <= horizon:
            alerts.append(
                EmployeeProfileAlertRead(
                    code="contract_expiring",
                    severity="warning",
                    title="Contrato por vencer",
                    message=f"Vence en {_days_until(end, today)} días ({end.isoformat()}).",
                    due_date=end,
                )
            )

    if labor and labor.contract_type == "fijo" and not labor.contract_end_date:
        alerts.append(
            EmployeeProfileAlertRead(
                code="contract_end_missing",
                severity="warning",
                title="Fecha de vencimiento pendiente",
                message="Contrato a término fijo sin fecha de vencimiento registrada.",
            )
        )

    docs = list(emp.documents or [])
    kinds_present = {d.document_kind for d in docs}
    for kind in _REQUIRED_DOC_KINDS:
        if kind not in kinds_present:
            alerts.append(
                EmployeeProfileAlertRead(
                    code=f"document_missing_{kind}",
                    severity="warning",
                    title="Documento pendiente",
                    message=f"Falta cargar documento: {kind}.",
                )
            )

    for doc in docs:
        status = effective_document_status(doc, today)
        if status == "pendiente":
            alerts.append(
                EmployeeProfileAlertRead(
                    code=f"document_pending_{doc.id}",
                    severity="info",
                    title="Documento pendiente de validación",
                    message=f"«{doc.display_name}» está pendiente.",
                )
            )
        if doc.expires_at:
            if doc.expires_at < today:
                alerts.append(
                    EmployeeProfileAlertRead(
                        code=f"document_expired_{doc.id}",
                        severity="critical",
                        title="Documento vencido",
                        message=f"«{doc.display_name}» venció el {doc.expires_at.isoformat()}.",
                        due_date=doc.expires_at,
                    )
                )
            elif doc.expires_at <= horizon:
                alerts.append(
                    EmployeeProfileAlertRead(
                        code=f"document_expiring_{doc.id}",
                        severity="warning",
                        title="Documento por vencer",
                        message=f"«{doc.display_name}» vence el {doc.expires_at.isoformat()}.",
                        due_date=doc.expires_at,
                    )
                )

    for lic in emp.driving_licenses or []:
        if lic.expires_at:
            if lic.expires_at < today:
                alerts.append(
                    EmployeeProfileAlertRead(
                        code=f"license_expired_{lic.id}",
                        severity="critical",
                        title="Licencia de conducción vencida",
                        message=f"Categoría {lic.category} venció el {lic.expires_at.isoformat()}.",
                        due_date=lic.expires_at,
                    )
                )
            elif lic.expires_at <= horizon:
                alerts.append(
                    EmployeeProfileAlertRead(
                        code=f"license_expiring_{lic.id}",
                        severity="warning",
                        title="Licencia por vencer",
                        message=f"Categoría {lic.category} vence el {lic.expires_at.isoformat()}.",
                        due_date=lic.expires_at,
                    )
                )

    for cert in emp.work_sst_certs or []:
        if cert.expires_at:
            if cert.expires_at < today:
                alerts.append(
                    EmployeeProfileAlertRead(
                        code=f"sst_cert_expired_{cert.id}",
                        severity="critical",
                        title="Certificación SST vencida",
                        message=f"Certificación «{cert.cert_type}» venció el {cert.expires_at.isoformat()}.",
                        due_date=cert.expires_at,
                    )
                )
            elif cert.expires_at <= horizon:
                alerts.append(
                    EmployeeProfileAlertRead(
                        code=f"sst_cert_expiring_{cert.id}",
                        severity="warning",
                        title="Certificación SST por vencer",
                        message=f"«{cert.cert_type}» vence el {cert.expires_at.isoformat()}.",
                        due_date=cert.expires_at,
                    )
                )

    if personal and personal.birth_date:
        nb = _next_birthday(personal.birth_date, today)
        if _days_until(nb, today) <= BIRTHDAY_HORIZON_DAYS:
            alerts.append(
                EmployeeProfileAlertRead(
                    code="birthday_upcoming",
                    severity="info",
                    title="Cumpleaños próximo",
                    message=f"Cumpleaños el {nb.strftime('%d/%m')}.",
                    due_date=nb,
                )
            )

    sst = emp.sst_profile
    if sst is None or sst.entry_exam_date is None:
        alerts.append(
            EmployeeProfileAlertRead(
                code="entry_exam_missing",
                severity="warning",
                title="Examen de ingreso",
                message="No hay examen de ingreso registrado.",
            )
        )

    exams = [e for e in (emp.sst_periodic_exams or []) if e.exam_date]
    if exams:
        last = max(e.exam_date for e in exams if e.exam_date)
        if last and last < today - timedelta(days=PERIODIC_EXAM_MONTHS * 30):
            alerts.append(
                EmployeeProfileAlertRead(
                    code="periodic_exam_overdue",
                    severity="warning",
                    title="Examen periódico",
                    message=f"Último examen registrado: {last.isoformat()}. Revise periodicidad.",
                    due_date=last,
                )
            )
    elif sst and sst.entry_exam_date:
        if sst.entry_exam_date < today - timedelta(days=PERIODIC_EXAM_MONTHS * 30):
            alerts.append(
                EmployeeProfileAlertRead(
                    code="periodic_exam_missing",
                    severity="info",
                    title="Sin exámenes periódicos",
                    message="No hay exámenes periódicos registrados tras el ingreso.",
                )
            )

    completeness = _completeness_percent(
        emp,
        personal,
        labor,
        list(emp.dependents or []),
        docs,
        list(emp.education_records or []),
        list(emp.training_records or []),
        list(emp.prior_jobs or []),
        list(emp.languages or []),
        sst,
    )
    if completeness < 50:
        alerts.append(
            EmployeeProfileAlertRead(
                code="profile_incomplete",
                severity="info",
                title="Expediente incompleto",
                message=f"Completitud del expediente: {completeness}%.",
            )
        )

    return alerts


async def _can_see_alerts(db: AsyncSession, actor: User) -> bool:
    if not await user_has_any_permission(db, actor, PERM_PROFILE_ALERTS):
        return False
    return await user_can_view_full_profile(db, actor)


async def _load_employees_for_alerts(db: AsyncSession, actor: User) -> list[Employee]:
    q = (
        select(Employee)
        .where(Employee.status == EntityStatus.ACTIVE.value)
        .options(
            selectinload(Employee.area),
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


async def get_employee_alerts(
    db: AsyncSession,
    actor: User,
    employee_id: int,
) -> EmployeeProfileAlertsBundleRead:
    if not await _can_see_alerts(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para ver alertas del expediente")
    emp = await _load_employee_profile(db, employee_id)
    if not emp:
        from app.core.exceptions import not_found

        raise not_found()
    ensure_employee_access(actor, emp)
    alerts = compute_employee_alerts(emp)
    return EmployeeProfileAlertsBundleRead(
        employee_id=emp.id,
        employee_name=emp.name,
        identification_number=emp.identification_number,
        alerts=alerts,
    )


async def list_all_profile_alerts(
    db: AsyncSession,
    actor: User,
) -> EmployeeProfileAlertsListRead:
    if not await _can_see_alerts(db, actor):
        from app.core.exceptions import forbidden

        raise forbidden("No tiene permiso para ver alertas del expediente")
    employees = await _load_employees_for_alerts(db, actor)
    items: list[EmployeeProfileAlertsBundleRead] = []
    total = 0
    with_alerts = 0
    for emp in employees:
        ensure_employee_access(actor, emp)
        alerts = compute_employee_alerts(emp)
        if alerts:
            with_alerts += 1
            total += len(alerts)
        items.append(
            EmployeeProfileAlertsBundleRead(
                employee_id=emp.id,
                employee_name=emp.name,
                identification_number=emp.identification_number,
                alerts=alerts,
            )
        )
    items.sort(key=lambda x: (-len(x.alerts), x.employee_name))
    return EmployeeProfileAlertsListRead(
        items=items,
        total_alerts=total,
        employees_with_alerts=with_alerts,
    )

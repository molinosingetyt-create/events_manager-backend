"""Novedades de nómina e integración con datos laborales."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import forbidden, not_found
from app.models.employee import Employee
from app.models.employee_custom import EmployeePayrollEntry
from app.models.user import User
from app.schemas.employee_profile_phase6 import (
    EmployeePayrollEntryRead,
    EmployeePayrollEntryWrite,
    EmployeePayrollSummaryRead,
)
from app.services.employee_profile_service import PERM_PAYROLL, _load_employee_profile
from app.services.employee_service import ensure_employee_access, get_employee
from app.services.rbac_service import user_has_any_permission


def _money(val: Decimal | float | int | None) -> float | None:
    if val is None:
        return None
    return float(val)


def payroll_summary_from_employee(emp: Employee) -> EmployeePayrollSummaryRead:
    labor = emp.labor
    if labor is None:
        return EmployeePayrollSummaryRead()
    return EmployeePayrollSummaryRead(
        base_salary=_money(labor.base_salary),
        eps_name=labor.eps_name,
        eps_affiliation_number=labor.eps_affiliation_number,
        pension_fund=labor.pension_fund,
        severance_fund=labor.severance_fund,
        family_compensation_box=labor.family_compensation_box,
        arl_name=labor.arl_name,
        bank_name=labor.bank_name,
        bank_account_type=labor.bank_account_type,
        bank_account_number=labor.bank_account_number,
        notes=labor.notes,
    )


def payroll_entry_read(row: EmployeePayrollEntry) -> EmployeePayrollEntryRead:
    creator = row.created_by.name if row.created_by is not None else None
    return EmployeePayrollEntryRead(
        id=row.id,
        period_month=row.period_month,
        concept_type=row.concept_type,  # type: ignore[arg-type]
        description=row.description,
        amount=_money(row.amount),
        reference_code=row.reference_code,
        notes=row.notes,
        source=row.source,  # type: ignore[arg-type]
        created_by_name=creator,
    )


async def user_can_edit_payroll(db: AsyncSession, user: User) -> bool:
    return await user_has_any_permission(db, user, PERM_PAYROLL)


async def user_can_view_payroll(db: AsyncSession, user: User) -> bool:
    if await user_can_edit_payroll(db, user):
        return True
    return await user_has_any_permission(db, user, "employees.profile.full")


async def list_payroll_entries(
    db: AsyncSession,
    actor: User,
    employee_id: int,
) -> list[EmployeePayrollEntryRead]:
    if not await user_can_view_payroll(db, actor):
        raise forbidden("No tiene permiso para ver nómina")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    r = await db.execute(
        select(EmployeePayrollEntry)
        .options(selectinload(EmployeePayrollEntry.created_by))
        .where(EmployeePayrollEntry.employee_id == employee_id)
        .order_by(EmployeePayrollEntry.period_month.desc(), EmployeePayrollEntry.id.desc())
    )
    return [payroll_entry_read(row) for row in r.scalars().all()]


async def get_payroll_bundle(
    db: AsyncSession,
    actor: User,
    employee_id: int,
) -> tuple[EmployeePayrollSummaryRead, list[EmployeePayrollEntryRead]]:
    if not await user_can_view_payroll(db, actor):
        raise forbidden("No tiene permiso para ver nómina")
    emp = await _load_employee_profile(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    entries = await list_payroll_entries(db, actor, employee_id)
    return payroll_summary_from_employee(emp), entries


async def _sync_payroll_entries(
    db: AsyncSession,
    emp: Employee,
    actor: User,
    items: list[EmployeePayrollEntryWrite] | None,
) -> None:
    if items is None:
        return
    if not await user_can_edit_payroll(db, actor):
        raise forbidden("No tiene permiso para editar nómina")
    await db.execute(delete(EmployeePayrollEntry).where(EmployeePayrollEntry.employee_id == emp.id))
    for item in items:
        db.add(
            EmployeePayrollEntry(
                employee_id=emp.id,
                period_month=item.period_month,
                concept_type=item.concept_type,
                description=item.description.strip(),
                amount=Decimal(str(item.amount)) if item.amount is not None else None,
                reference_code=item.reference_code,
                notes=item.notes,
                source=item.source,
                created_by_id=actor.id,
            )
        )
    await db.flush()


async def replace_payroll_entries(
    db: AsyncSession,
    actor: User,
    employee_id: int,
    items: list[EmployeePayrollEntryWrite],
) -> list[EmployeePayrollEntryRead]:
    if not await user_can_edit_payroll(db, actor):
        raise forbidden("No tiene permiso para editar nómina")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found()
    ensure_employee_access(actor, emp)
    await _sync_payroll_entries(db, emp, actor, items)
    await db.commit()
    return await list_payroll_entries(db, actor, employee_id)

"""Definición y valores de campos personalizados."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.employee import Employee
from app.models.employee_custom import EmployeeCustomFieldDef, EmployeeCustomFieldValue
from app.models.user import User
from app.schemas.employee_profile_phase6 import (
    EmployeeCustomFieldDefCreate,
    EmployeeCustomFieldDefRead,
    EmployeeCustomFieldDefUpdate,
    EmployeeCustomFieldValueRead,
    EmployeeCustomFieldValueWrite,
    options_from_json,
    options_to_json,
)
from app.services.employee_profile_service import PERM_CUSTOM_MANAGE, user_can_edit_profile
from app.services.employee_service import ensure_employee_access, get_employee
from app.services.rbac_service import user_has_any_permission

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _def_read(row: EmployeeCustomFieldDef) -> EmployeeCustomFieldDefRead:
    return EmployeeCustomFieldDefRead(
        id=row.id,
        field_key=row.field_key,
        label=row.label,
        field_type=row.field_type,  # type: ignore[arg-type]
        section=row.section,
        options=options_from_json(row.options_json),
        is_required=row.is_required,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )


async def user_can_manage_custom_fields(db: AsyncSession, user: User) -> bool:
    return await user_has_any_permission(db, user, PERM_CUSTOM_MANAGE)


async def list_field_definitions(
    db: AsyncSession,
    actor: User,
    *,
    active_only: bool = True,
) -> list[EmployeeCustomFieldDefRead]:
    if not await user_can_manage_custom_fields(db, actor):
        if not await user_has_any_permission(db, actor, "employees.profile.full"):
            raise forbidden("No tiene permiso para ver campos personalizados")
    q = select(EmployeeCustomFieldDef).order_by(
        EmployeeCustomFieldDef.sort_order, EmployeeCustomFieldDef.label
    )
    if active_only:
        q = q.where(EmployeeCustomFieldDef.is_active.is_(True))
    r = await db.execute(q)
    return [_def_read(row) for row in r.scalars().all()]


async def list_all_definitions_admin(
    db: AsyncSession, actor: User
) -> list[EmployeeCustomFieldDefRead]:
    if not await user_can_manage_custom_fields(db, actor):
        raise forbidden("No tiene permiso para administrar campos personalizados")
    r = await db.execute(
        select(EmployeeCustomFieldDef).order_by(
            EmployeeCustomFieldDef.sort_order, EmployeeCustomFieldDef.label
        )
    )
    return [_def_read(row) for row in r.scalars().all()]


async def create_field_definition(
    db: AsyncSession,
    actor: User,
    body: EmployeeCustomFieldDefCreate,
) -> EmployeeCustomFieldDefRead:
    if not await user_can_manage_custom_fields(db, actor):
        raise forbidden("No tiene permiso para administrar campos personalizados")
    key = body.field_key.strip().lower()
    if not _KEY_RE.match(key):
        raise bad_request("La clave debe usar solo minúsculas, números y guión bajo (iniciar con letra)")
    if body.field_type == "select" and not body.options:
        raise bad_request("Los campos tipo lista deben incluir opciones")
    row = EmployeeCustomFieldDef(
        field_key=key,
        label=body.label.strip(),
        field_type=body.field_type,
        section=body.section,
        options_json=options_to_json(body.options),
        is_required=body.is_required,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _def_read(row)


async def update_field_definition(
    db: AsyncSession,
    actor: User,
    field_id: int,
    body: EmployeeCustomFieldDefUpdate,
) -> EmployeeCustomFieldDefRead:
    if not await user_can_manage_custom_fields(db, actor):
        raise forbidden("No tiene permiso para administrar campos personalizados")
    r = await db.execute(select(EmployeeCustomFieldDef).where(EmployeeCustomFieldDef.id == field_id))
    row = r.scalar_one_or_none()
    if not row:
        raise not_found("Campo no encontrado")
    data = body.model_dump(exclude_unset=True)
    if "options" in data:
        opts = data.pop("options")
        row.options_json = options_to_json(opts or [])
    for k, v in data.items():
        setattr(row, k, v)
    if row.field_type == "select" and not options_from_json(row.options_json):
        raise bad_request("Los campos tipo lista deben incluir opciones")
    await db.commit()
    await db.refresh(row)
    return _def_read(row)


async def delete_field_definition(db: AsyncSession, actor: User, field_id: int) -> None:
    if not await user_can_manage_custom_fields(db, actor):
        raise forbidden("No tiene permiso para administrar campos personalizados")
    r = await db.execute(select(EmployeeCustomFieldDef).where(EmployeeCustomFieldDef.id == field_id))
    row = r.scalar_one_or_none()
    if not row:
        raise not_found("Campo no encontrado")
    await db.delete(row)
    await db.commit()


def build_custom_fields_for_employee(emp: Employee) -> list[EmployeeCustomFieldValueRead]:
    values_map = {v.field_def_id: v for v in (emp.custom_field_values or [])}
    out: list[EmployeeCustomFieldValueRead] = []
    for val in emp.custom_field_values or []:
        d = val.field_def
        if d is None or not d.is_active:
            continue
        out.append(
            EmployeeCustomFieldValueRead(
                field_def_id=d.id,
                field_key=d.field_key,
                label=d.label,
                field_type=d.field_type,  # type: ignore[arg-type]
                section=d.section,
                options=options_from_json(d.options_json),
                is_required=d.is_required,
                value=val.value_text,
            )
        )
    return sorted(out, key=lambda x: (x.section or "", x.label))


async def load_active_defs(db: AsyncSession) -> list[EmployeeCustomFieldDef]:
    r = await db.execute(
        select(EmployeeCustomFieldDef)
        .where(EmployeeCustomFieldDef.is_active.is_(True))
        .order_by(EmployeeCustomFieldDef.sort_order, EmployeeCustomFieldDef.label)
    )
    return list(r.scalars().all())


async def sync_custom_field_values(
    db: AsyncSession,
    emp: Employee,
    items: list[EmployeeCustomFieldValueWrite] | None,
) -> None:
    if items is None:
        return
    defs = await load_active_defs(db)
    defs_by_key = {d.field_key: d for d in defs}
    existing = {v.field_def_id: v for v in (emp.custom_field_values or [])}

    for item in items:
        d = defs_by_key.get(item.field_key)
        if not d:
            raise bad_request(f"Campo personalizado desconocido: {item.field_key}")
        val = (item.value or "").strip() if item.value is not None else ""
        if d.is_required and not val and d.field_type != "boolean":
            raise bad_request(f"El campo «{d.label}» es obligatorio")
        if d.field_type == "boolean" and val and val not in ("true", "false", "1", "0", "si", "sí", "no"):
            raise bad_request(f"Valor booleano inválido en «{d.label}»")
        if d.field_type == "select" and val:
            opts = options_from_json(d.options_json)
            if opts and val not in opts:
                raise bad_request(f"Valor no permitido en «{d.label}»")
        row = existing.get(d.id)
        if row:
            row.value_text = val or None
        else:
            db.add(
                EmployeeCustomFieldValue(
                    employee_id=emp.id,
                    field_def_id=d.id,
                    value_text=val or None,
                )
            )
    await db.flush()


async def merge_custom_fields_read(
    db: AsyncSession, emp: Employee
) -> list[EmployeeCustomFieldValueRead]:
    defs = await load_active_defs(db)
    val_map = {v.field_def_id: v.value_text for v in (emp.custom_field_values or [])}
    out: list[EmployeeCustomFieldValueRead] = []
    for d in defs:
        out.append(
            EmployeeCustomFieldValueRead(
                field_def_id=d.id,
                field_key=d.field_key,
                label=d.label,
                field_type=d.field_type,  # type: ignore[arg-type]
                section=d.section,
                options=options_from_json(d.options_json),
                is_required=d.is_required,
                value=val_map.get(d.id),
            )
        )
    return out

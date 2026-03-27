import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_roles
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services import audit_service
from app.services import employee_service as svc

router = APIRouter()


def _employee_read(e: Employee) -> EmployeeRead:
    area_name = e.area.name if e.area is not None else ""
    leader_name = e.leader_user.name if e.leader_user is not None else None
    return EmployeeRead(
        id=e.id,
        name=e.name,
        identification_number=e.identification_number,
        position=e.position,
        area_id=e.area_id,
        area_name=area_name,
        leader_id=e.leader_id,
        leader_name=leader_name,
        status=e.status,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


@router.get("", response_model=PaginatedResponse[EmployeeRead])
async def list_employees(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    area_id: int | None = None,
    leader_id: int | None = None,
) -> PaginatedResponse[EmployeeRead]:
    items, total = await svc.list_employees_for_actor(
        db,
        current,
        page=page,
        page_size=page_size,
        area_id=area_id,
        leader_id=leader_id,
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.list",
        entity_type="employee",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_employee_read(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=EmployeeRead)
async def create_employee(
    request: Request,
    body: EmployeeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_roles(Role.ADMIN, Role.HR))],
) -> EmployeeRead:
    e = await svc.create_employee(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.create",
        entity_type="employee",
        entity_id=e.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _employee_read(e)


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> EmployeeRead:
    e = await svc.get_employee(db, employee_id)
    if not e:
        from app.core.exceptions import not_found

        raise not_found()
    svc.ensure_employee_access(current, e)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.get",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _employee_read(e)


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    request: Request,
    employee_id: int,
    body: EmployeeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_roles(Role.ADMIN, Role.HR))],
) -> EmployeeRead:
    e = await svc.get_employee(db, employee_id)
    if not e:
        from app.core.exceptions import not_found

        raise not_found()
    e2 = await svc.update_employee(db, employee_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.update",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _employee_read(e2)


@router.delete("/{employee_id}")
async def delete_employee(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_roles(Role.ADMIN, Role.HR))],
) -> dict[str, str]:
    await svc.delete_employee(db, employee_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.delete",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return {"detail": "Operación correcta"}

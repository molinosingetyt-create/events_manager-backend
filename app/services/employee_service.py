from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.employee import Employee
from app.models.enums import EntityStatus, Role
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.incapacity_catalog_service import require_active_temporal_category
from app.services.rbac_service import behavior_key


async def validate_leader(
    db: AsyncSession,
    leader_id: int | None,
    area_id: int,
    *,
    actor: User,
) -> None:
    if leader_id is None:
        return
    r = await db.execute(select(User).options(selectinload(User.profile)).where(User.id == leader_id))
    leader = r.scalar_one_or_none()
    if not leader:
        raise bad_request("Usuario asignado no encontrado")
    if leader.status != EntityStatus.ACTIVE.value:
        raise bad_request("El usuario asignado debe estar activo")
    if leader.area_id != area_id:
        raise bad_request("El líder debe pertenecer al mismo área que el empleado")
    if behavior_key(actor) == Role.ADMIN.value:
        return
    if behavior_key(leader) != Role.LEADER.value:
        raise bad_request("Solo administración puede asignar un usuario que no sea líder; indique un usuario con rol LÍDER")


async def get_employee(db: AsyncSession, employee_id: int) -> Employee | None:
    r = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.area),
            selectinload(Employee.leader_user),
            selectinload(Employee.temporal_category),
        )
        .where(Employee.id == employee_id)
    )
    return r.scalar_one_or_none()


async def list_employees_for_actor(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    area_id: int | None = None,
    leader_id: int | None = None,
    search: str | None = None,
) -> tuple[list[Employee], int]:
    q = select(Employee).options(
        selectinload(Employee.area),
        selectinload(Employee.leader_user),
        selectinload(Employee.temporal_category),
    )
    count_q = select(func.count()).select_from(Employee)

    if search and search.strip():
        term = f"%{search.strip()}%"
        cond = or_(Employee.name.ilike(term), Employee.identification_number.ilike(term))
        q = q.where(cond)
        count_q = count_q.where(cond)

    if behavior_key(actor) == Role.LEADER.value:
        q = q.where(Employee.leader_id == actor.id)
        count_q = count_q.where(Employee.leader_id == actor.id)
    else:
        if area_id is not None:
            q = q.where(Employee.area_id == area_id)
            count_q = count_q.where(Employee.area_id == area_id)
        if leader_id is not None:
            q = q.where(Employee.leader_id == leader_id)
            count_q = count_q.where(Employee.leader_id == leader_id)

    total = (await db.execute(count_q)).scalar_one()
    q = q.order_by(Employee.id).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def create_employee(db: AsyncSession, data: EmployeeCreate, *, actor: User) -> Employee:
    dup = await db.execute(
        select(Employee).where(Employee.identification_number == data.identification_number)
    )
    if dup.scalar_one_or_none():
        raise bad_request("El número de identificación ya existe")

    await validate_leader(db, data.leader_id, data.area_id, actor=actor)
    await require_active_temporal_category(db, data.temporal_category_id)

    emp = Employee(
        name=data.name,
        identification_number=data.identification_number,
        position=data.position,
        area_id=data.area_id,
        leader_id=data.leader_id,
        temporal_category_id=data.temporal_category_id,
        status=data.status.value,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


async def update_employee(db: AsyncSession, employee_id: int, data: EmployeeUpdate, *, actor: User) -> Employee:
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found("Empleado no encontrado")

    new_area = data.area_id if data.area_id is not None else emp.area_id
    new_leader = data.leader_id if data.leader_id is not None else emp.leader_id
    if data.leader_id is not None or data.area_id is not None:
        await validate_leader(db, new_leader, new_area, actor=actor)

    if data.name is not None:
        emp.name = data.name
    if data.identification_number is not None:
        dup = await db.execute(
            select(Employee).where(
                Employee.identification_number == data.identification_number,
                Employee.id != employee_id,
            )
        )
        if dup.scalar_one_or_none():
            raise bad_request("El número de identificación ya existe")
        emp.identification_number = data.identification_number
    if data.position is not None:
        emp.position = data.position
    if data.area_id is not None:
        emp.area_id = data.area_id
    if data.leader_id is not None:
        emp.leader_id = data.leader_id
    if data.temporal_category_id is not None:
        await require_active_temporal_category(db, data.temporal_category_id)
        emp.temporal_category_id = data.temporal_category_id
    if data.status is not None:
        emp.status = data.status.value

    await db.commit()
    reloaded = await get_employee(db, employee_id)
    return reloaded or emp


async def delete_employee(db: AsyncSession, employee_id: int) -> None:
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found("Empleado no encontrado")
    emp.status = EntityStatus.INACTIVE.value
    await db.commit()


def ensure_employee_access(actor: User, emp: Employee) -> None:
    if behavior_key(actor) == Role.LEADER.value and emp.leader_id != actor.id:
        raise forbidden("Solo puede ver empleados asignados a usted como líder")



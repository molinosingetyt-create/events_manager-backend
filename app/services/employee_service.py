from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.employee import Employee
from app.models.enums import EntityStatus, Role
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


async def validate_leader(db: AsyncSession, leader_id: int | None, area_id: int) -> None:
    if leader_id is None:
        return
    r = await db.execute(select(User).where(User.id == leader_id))
    leader = r.scalar_one_or_none()
    if not leader:
        raise bad_request("Usuario líder no encontrado")
    if leader.role != Role.LEADER.value:
        raise bad_request("leader_id debe ser un usuario con rol LÍDER")
    if leader.area_id != area_id:
        raise bad_request("El líder debe pertenecer al mismo área que el empleado")


async def get_employee(db: AsyncSession, employee_id: int) -> Employee | None:
    r = await db.execute(
        select(Employee)
        .options(selectinload(Employee.area), selectinload(Employee.leader_user))
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
) -> tuple[list[Employee], int]:
    q = select(Employee).options(
        selectinload(Employee.area),
        selectinload(Employee.leader_user),
    )
    count_q = select(func.count()).select_from(Employee)

    if actor.role == Role.LEADER.value:
        q = q.where(Employee.area_id == actor.area_id)
        count_q = count_q.where(Employee.area_id == actor.area_id)
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


async def create_employee(db: AsyncSession, data: EmployeeCreate) -> Employee:
    dup = await db.execute(
        select(Employee).where(Employee.identification_number == data.identification_number)
    )
    if dup.scalar_one_or_none():
        raise bad_request("El número de identificación ya existe")

    await validate_leader(db, data.leader_id, data.area_id)

    emp = Employee(
        name=data.name,
        identification_number=data.identification_number,
        position=data.position,
        area_id=data.area_id,
        leader_id=data.leader_id,
        status=data.status.value,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


async def update_employee(db: AsyncSession, employee_id: int, data: EmployeeUpdate) -> Employee:
    emp = await get_employee(db, employee_id)
    if not emp:
        raise not_found("Empleado no encontrado")

    new_area = data.area_id if data.area_id is not None else emp.area_id
    new_leader = data.leader_id if data.leader_id is not None else emp.leader_id
    if data.leader_id is not None or data.area_id is not None:
        await validate_leader(db, new_leader, new_area)

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
    if actor.role == Role.LEADER.value and emp.area_id != actor.area_id:
        raise forbidden("No puede acceder a empleados fuera de su área")



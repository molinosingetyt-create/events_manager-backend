from collections import defaultdict

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.area import Area
from app.models.employee import Employee
from app.models.employee_profile import EmployeeLabor
from app.models.enums import EntityStatus, Role
from app.models.profile import Profile
from app.models.user import User
from app.schemas.employee_profile import DOCUMENT_KIND_LABELS, EmployeeFilterOptionsRead
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    OrgChartMemberRead,
    OrgChartNodeRead,
    OrgChartTreeResponse,
)
from app.services.incapacity_catalog_service import require_active_temporal_category
from app.services.rbac_service import behavior_key


def acts_as_team_leader(user: User) -> bool:
    """Usuario que opera con alcance de equipo (perfil o rol de líder)."""
    if behavior_key(user) == Role.LEADER.value:
        return True
    return user.role == Role.LEADER.value


def _scoped_to_led_team(
    actor: User,
    *,
    team_only: bool,
    leader_id: int | None,
) -> bool:
    if team_only:
        return True
    if acts_as_team_leader(actor):
        return True
    return leader_id is not None and leader_id == actor.id


async def validate_leader(
    db: AsyncSession,
    leader_id: int | None,
    _employee_area_id: int,
    *,
    actor: User,
) -> None:
    """Usuario existe y está activo; salvo administración, debe tener comportamiento LÍDER (área del líder libre)."""
    if leader_id is None:
        return
    r = await db.execute(select(User).options(selectinload(User.profile)).where(User.id == leader_id))
    leader = r.scalar_one_or_none()
    if not leader:
        raise bad_request("Usuario asignado no encontrado")
    if leader.status != EntityStatus.ACTIVE.value:
        raise bad_request("El usuario asignado debe estar activo")
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


def _employee_list_base():
    return select(Employee).outerjoin(
        EmployeeLabor, EmployeeLabor.employee_id == Employee.id
    )


def _apply_employee_list_filters(
    q,
    count_q,
    *,
    search: str | None,
    status: str | None,
    area_id: int | None,
    leader_id: int | None,
    work_site_city: str | None,
    hierarchical_level: str | None,
    contract_type: str | None,
    collaborator_status: str | None,
    linkage_type: str | None,
):
    if search and search.strip():
        term = f"%{search.strip()}%"
        cond = or_(Employee.name.ilike(term), Employee.identification_number.ilike(term))
        q = q.where(cond)
        count_q = count_q.where(cond)
    if status and status.strip():
        q = q.where(Employee.status == status.strip())
        count_q = count_q.where(Employee.status == status.strip())
    if area_id is not None:
        q = q.where(Employee.area_id == area_id)
        count_q = count_q.where(Employee.area_id == area_id)
    if leader_id is not None:
        q = q.where(Employee.leader_id == leader_id)
        count_q = count_q.where(Employee.leader_id == leader_id)
    if work_site_city and work_site_city.strip():
        q = q.where(EmployeeLabor.work_site_city == work_site_city.strip())
        count_q = count_q.where(EmployeeLabor.work_site_city == work_site_city.strip())
    if hierarchical_level and hierarchical_level.strip():
        q = q.where(EmployeeLabor.hierarchical_level == hierarchical_level.strip())
        count_q = count_q.where(EmployeeLabor.hierarchical_level == hierarchical_level.strip())
    if contract_type and contract_type.strip():
        q = q.where(EmployeeLabor.contract_type == contract_type.strip())
        count_q = count_q.where(EmployeeLabor.contract_type == contract_type.strip())
    if collaborator_status and collaborator_status.strip():
        q = q.where(EmployeeLabor.collaborator_status == collaborator_status.strip())
        count_q = count_q.where(EmployeeLabor.collaborator_status == collaborator_status.strip())
    if linkage_type and linkage_type.strip():
        q = q.where(EmployeeLabor.linkage_type == linkage_type.strip())
        count_q = count_q.where(EmployeeLabor.linkage_type == linkage_type.strip())
    return q, count_q


async def list_employees_for_actor(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    area_id: int | None = None,
    leader_id: int | None = None,
    search: str | None = None,
    team_only: bool = False,
    status: str | None = None,
    work_site_city: str | None = None,
    hierarchical_level: str | None = None,
    contract_type: str | None = None,
    collaborator_status: str | None = None,
    linkage_type: str | None = None,
) -> tuple[list[Employee], int]:
    q = _employee_list_base().options(
        selectinload(Employee.area),
        selectinload(Employee.leader_user),
        selectinload(Employee.temporal_category),
    )
    count_q = (
        select(func.count(func.distinct(Employee.id)))
        .select_from(Employee)
        .outerjoin(EmployeeLabor, EmployeeLabor.employee_id == Employee.id)
    )

    if _scoped_to_led_team(actor, team_only=team_only, leader_id=leader_id):
        q = q.where(Employee.leader_id == actor.id)
        count_q = count_q.where(Employee.leader_id == actor.id)
        q, count_q = _apply_employee_list_filters(
            q,
            count_q,
            search=search,
            status=status,
            area_id=None,
            leader_id=None,
            work_site_city=work_site_city,
            hierarchical_level=hierarchical_level,
            contract_type=contract_type,
            collaborator_status=collaborator_status,
            linkage_type=linkage_type,
        )
    else:
        q, count_q = _apply_employee_list_filters(
            q,
            count_q,
            search=search,
            status=status,
            area_id=area_id,
            leader_id=leader_id,
            work_site_city=work_site_city,
            hierarchical_level=hierarchical_level,
            contract_type=contract_type,
            collaborator_status=collaborator_status,
            linkage_type=linkage_type,
        )

    total = (await db.execute(count_q)).scalar_one()
    q = q.distinct().order_by(Employee.id).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_employee_filter_options(
    db: AsyncSession,
    actor: User,
) -> EmployeeFilterOptionsRead:
    areas_r = await db.execute(
        select(Area.id, Area.name).where(Area.status == EntityStatus.ACTIVE.value).order_by(Area.name)
    )
    areas = [{"id": row[0], "name": row[1]} for row in areas_r.all()]

    leaders: list[dict[str, int | str]] = []
    if not acts_as_team_leader(actor):
        leaders_r = await db.execute(
            select(User.id, User.name)
            .join(Profile, User.profile_id == Profile.id)
            .where(
                User.status == EntityStatus.ACTIVE.value,
                Profile.behavior_key == Role.LEADER.value,
            )
            .order_by(User.name)
        )
        leaders = [{"id": row[0], "name": row[1]} for row in leaders_r.all()]

    def distinct_labor(col):
        return select(col).where(col.isnot(None), col != "").distinct().order_by(col)

    cities = [
        r[0]
        for r in (
            await db.execute(distinct_labor(EmployeeLabor.work_site_city))
        ).all()
    ]
    levels = [r[0] for r in (await db.execute(distinct_labor(EmployeeLabor.hierarchical_level))).all()]
    contracts = [r[0] for r in (await db.execute(distinct_labor(EmployeeLabor.contract_type))).all()]
    collab = [r[0] for r in (await db.execute(distinct_labor(EmployeeLabor.collaborator_status))).all()]
    links = [r[0] for r in (await db.execute(distinct_labor(EmployeeLabor.linkage_type))).all()]

    return EmployeeFilterOptionsRead(
        areas=areas,
        leaders=leaders,
        work_site_cities=cities,
        hierarchical_levels=levels,
        contract_types=contracts,
        collaborator_statuses=collab,
        linkage_types=links,
        document_kinds=[{"value": k, "label": v} for k, v in DOCUMENT_KIND_LABELS.items()],
    )


async def list_assignable_employees_for_actor(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[list[Employee], int]:
    """Empleados para formularios (horas extra, incapacidades): equipo del líder sin filtro por área."""
    bk = behavior_key(actor)
    if bk in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        return await list_employees_for_actor(
            db, actor, page=page, page_size=page_size, search=search
        )
    return await list_employees_for_actor(
        db, actor, page=page, page_size=page_size, search=search, team_only=True
    )


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
    if acts_as_team_leader(actor) and emp.leader_id != actor.id:
        raise forbidden("Solo puede ver empleados asignados a usted como líder")


def _norm_person_name(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _employee_matched_leader_user_id(
    emp: Employee,
    leaders_who_lead: set[int],
    users_map: dict[int, User],
) -> int | None:
    """Si el empleado coincide con un usuario que también dirige equipo, devuelve ese `user.id`."""
    en = _norm_person_name(emp.name)
    matches: list[int] = []
    for uid in leaders_who_lead:
        u = users_map.get(uid)
        if u is None:
            continue
        if _norm_person_name(u.name) == en:
            matches.append(uid)
    if not matches:
        return None
    return min(matches)


async def get_organization_chart(db: AsyncSession) -> OrgChartTreeResponse:
    """Árbol único desde gerencia: anida equipos cuando el empleado coincide con un usuario líder (mismo nombre)."""
    r = await db.execute(select(Employee).options(selectinload(Employee.area)).order_by(Employee.name.asc()))
    employees = list(r.scalars().all())

    by_leader: dict[int | None, list[Employee]] = defaultdict(list)
    for e in employees:
        by_leader[e.leader_id].append(e)

    unassigned_src = by_leader.pop(None, [])

    leaders_who_lead: set[int] = {lid for lid in by_leader if lid is not None}

    mgmt_r = await db.execute(
        select(User)
        .join(Profile, User.profile_id == Profile.id)
        .where(Profile.behavior_key == Role.MANAGEMENT.value, User.status == EntityStatus.ACTIVE.value)
        .options(selectinload(User.profile), selectinload(User.area))
    )
    mgmt_users = list(mgmt_r.scalars().all())

    user_ids_to_load = set(leaders_who_lead) | {u.id for u in mgmt_users}
    users_map: dict[int, User] = {}
    if user_ids_to_load:
        ur = await db.execute(
            select(User)
            .where(User.id.in_(user_ids_to_load))
            .options(selectinload(User.profile), selectinload(User.area))
        )
        users_map = {u.id: u for u in ur.scalars().all()}

    unassigned = [
        OrgChartMemberRead(
            id=e.id,
            name=e.name,
            position=e.position,
            area_name=e.area.name if e.area is not None else "",
        )
        for e in sorted(unassigned_src, key=lambda x: x.name.lower())
    ]

    if not users_map:
        return OrgChartTreeResponse(roots=[], unassigned=unassigned)

    def build_employee_node(emp: Employee, placed: set[int]) -> OrgChartNodeRead:
        uid_match = _employee_matched_leader_user_id(emp, leaders_who_lead, users_map)
        children: list[OrgChartNodeRead] = []
        if uid_match is not None and uid_match not in placed:
            placed.add(uid_match)
            for sub in sorted(by_leader.get(uid_match, []), key=lambda x: x.name.lower()):
                children.append(build_employee_node(sub, placed))
        area_name = emp.area.name if emp.area is not None else ""
        return OrgChartNodeRead(
            kind="employee",
            user_id=None,
            employee_id=emp.id,
            name=emp.name,
            position_label=emp.position,
            area_name=area_name,
            children=children,
        )

    def orphan_leader_ids_for_root(root_uid: int, placed: set[int]) -> list[int]:
        root = users_map.get(root_uid)
        if root is None:
            return []
        out: list[int] = []
        for uid in sorted(leaders_who_lead):
            if uid == root_uid or uid in placed:
                continue
            u = users_map.get(uid)
            if u is None:
                continue
            if u.area_id != root.area_id:
                continue
            if behavior_key(u) == Role.MANAGEMENT.value:
                continue
            out.append(uid)
        return out

    def build_user_node(uid: int, placed: set[int], *, attach_area_orphans: bool) -> OrgChartNodeRead | None:
        if uid in placed:
            return None
        u = users_map.get(uid)
        if u is None:
            return None
        placed.add(uid)
        pos = u.profile.name if u.profile is not None else u.role
        area_name = u.area.name if u.area is not None else ""
        children: list[OrgChartNodeRead] = []
        for emp in sorted(by_leader.get(uid, []), key=lambda x: x.name.lower()):
            children.append(build_employee_node(emp, placed))
        if attach_area_orphans:
            for ouid in orphan_leader_ids_for_root(uid, placed):
                sub = build_user_node(ouid, placed, attach_area_orphans=False)
                if sub is not None:
                    children.append(sub)
        return OrgChartNodeRead(
            kind="user",
            user_id=u.id,
            employee_id=None,
            name=u.name,
            position_label=pos,
            area_name=area_name,
            children=children,
        )

    placed: set[int] = set()
    mgmt_sorted = sorted(
        mgmt_users,
        key=lambda u: (0 if u.id in leaders_who_lead else 1, u.name.lower()),
    )
    first_mgmt_id = mgmt_sorted[0].id if mgmt_sorted else None

    roots: list[OrgChartNodeRead] = []
    for mu in mgmt_sorted:
        node = build_user_node(mu.id, placed, attach_area_orphans=(mu.id == first_mgmt_id))
        if node is None:
            continue
        has_direct = mu.id in by_leader and len(by_leader[mu.id]) > 0
        if not node.children and not has_direct:
            continue
        roots.append(node)

    if not roots and leaders_who_lead:
        placed.clear()
        ordered = sorted(
            leaders_who_lead,
            key=lambda i: ((users_map[i].name.lower() if users_map.get(i) else ""), i),
        )
        first_uid = ordered[0]
        forest = []
        for uid in ordered:
            n = build_user_node(uid, placed, attach_area_orphans=(uid == first_uid))
            if n is not None:
                forest.append(n)
        if len(forest) > 1:
            roots = [
                OrgChartNodeRead(
                    kind="group",
                    name="Organización",
                    position_label="Equipos",
                    area_name="",
                    children=forest,
                )
            ]
        else:
            roots = forest

    if len(roots) > 1:
        roots = [
            OrgChartNodeRead(
                kind="group",
                name="Dirección",
                position_label="Gerencia",
                area_name="",
                children=roots,
            )
        ]

    return OrgChartTreeResponse(roots=roots, unassigned=unassigned)



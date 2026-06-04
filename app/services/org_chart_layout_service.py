from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, not_found
from app.models.employee import Employee
from app.models.org_chart_layout import OrgChartLayoutEdge, OrgChartLayoutNode
from app.models.user import User
from app.schemas.employee import OrgChartMemberRead, OrgChartNodeRead
from app.schemas.org_chart_layout import (
    ManualOrgChartResponse,
    OrgChartLayoutEdgeRead,
    OrgChartLayoutNodeCreate,
    OrgChartLayoutNodeRead,
    OrgChartLayoutNodeUpdate,
)


def _parents_of(edges: list[OrgChartLayoutEdge]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for e in edges:
        out[e.child_node_id].add(e.parent_node_id)
    return out


def _would_create_cycle(
    edges: list[OrgChartLayoutEdge],
    *,
    child_id: int,
    parent_id: int,
) -> bool:
    if child_id == parent_id:
        return True
    parents = _parents_of(edges)
    stack = [parent_id]
    seen: set[int] = set()
    while stack:
        nid = stack.pop()
        if nid == child_id:
            return True
        for pid in parents.get(nid, ()):
            if pid not in seen:
                seen.add(pid)
                stack.append(pid)
    return False


def _node_to_read(n: OrgChartLayoutNode) -> OrgChartLayoutNodeRead:
    return OrgChartLayoutNodeRead(
        id=n.id,
        name=n.name,
        position_label=n.position_label or "",
        area_name=n.area_name or "",
        sort_order=n.sort_order,
        is_chart_root=n.is_chart_root,
        employee_id=n.employee_id,
        user_id=n.user_id,
    )


def _node_in_forest(nodes: list[OrgChartNodeRead], layout_node_id: int) -> bool:
    stack = list(nodes)
    while stack:
        n = stack.pop()
        if n.layout_node_id == layout_node_id:
            return True
        stack.extend(n.children or [])
        if n.leaders:
            stack.extend(n.leaders)
    return False


def _is_reachable_from(
    target_id: int,
    start_ids: list[int],
    children_of: dict[int, list[int]],
) -> bool:
    seen: set[int] = set()
    stack = list(start_ids)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for cid in children_of.get(cur, []):
            if cid == target_id:
                return True
            stack.append(cid)
    return False


def _shared_immediate_boss(
    leader_ids: set[int],
    parents_map: dict[int, set[int]],
) -> int | None:
    """Jefe común inmediato de todos los líderes (p. ej. producción sobre 3 jefes de turno)."""
    common: set[int] | None = None
    for lid in leader_ids:
        bosses = parents_map.get(lid, set())
        if not bosses:
            return None
        if common is None:
            common = set(bosses)
        else:
            common &= bosses
    if not common:
        return None
    return min(common)


def _sort_node_ids(by_id: dict[int, OrgChartLayoutNode], ids: list[int] | set[int]) -> list[int]:
    return sorted(ids, key=lambda i: (by_id[i].sort_order, by_id[i].name.lower()))


def _manual_node_read(n: OrgChartLayoutNode, children: list[OrgChartNodeRead]) -> OrgChartNodeRead:
    return OrgChartNodeRead(
        kind="manual",
        user_id=n.user_id,
        employee_id=n.employee_id,
        layout_node_id=n.id,
        display_key=str(n.id),
        name=n.name,
        position_label=n.position_label or "",
        area_name=n.area_name or "",
        children=children,
    )


def _build_display_roots(
    nodes: list[OrgChartLayoutNode],
    edges: list[OrgChartLayoutEdge],
) -> list[OrgChartNodeRead]:
    by_id = {n.id: n for n in nodes}
    children_of: dict[int, list[int]] = defaultdict(list)
    parent_ids = set()
    for e in edges:
        children_of[e.parent_node_id].append(e.child_node_id)
        parent_ids.add(e.parent_node_id)

    parents_map = _parents_of(edges)
    multi_children: dict[int, set[int]] = {
        cid: pset for cid, pset in parents_map.items() if len(pset) > 1
    }
    # Varios operarios con los mismos jefes → un solo bloque (sin duplicar líderes).
    shelf_by_parents: dict[frozenset[int], list[int]] = defaultdict(list)
    for cid, pset in multi_children.items():
        shelf_by_parents[frozenset(pset)].append(cid)

    parents_in_shelf: set[int] = set()
    for pset in shelf_by_parents:
        parents_in_shelf.update(pset)

    child_ids = {e.child_node_id for e in edges}
    natural_roots = [
        n.id
        for n in nodes
        if n.id not in child_ids and (n.is_chart_root or n.id in parent_ids)
    ]
    forced_roots: set[int] = set()
    for pset_frozen in shelf_by_parents:
        boss_id = _shared_immediate_boss(set(pset_frozen), parents_map)
        if boss_id is not None and not _is_reachable_from(boss_id, natural_roots, children_of):
            forced_roots.add(boss_id)
    root_ids = _sort_node_ids(by_id, list(set(natural_roots) | forced_roots))
    if not root_ids and not multi_children:
        return []

    placed: set[int] = set()

    def build_leader_column(
        pid: int,
        path: tuple[int, ...],
        shelf_child_ids: set[int],
    ) -> OrgChartNodeRead:
        n = by_id[pid]
        path_set = frozenset(path)
        subs: list[OrgChartNodeRead] = []
        for cid in _sort_node_ids(by_id, children_of.get(pid, [])):
            if cid in shelf_child_ids or cid in placed or cid in path_set or cid in multi_children:
                continue
            placed.add(cid)
            subs.append(build_regular(cid, path + (pid,)))
        return _manual_node_read(n, subs)

    def build_shelf(
        parent_ids: set[int],
        shared_child_ids: list[int],
        path: tuple[int, ...],
    ) -> OrgChartNodeRead:
        shelf_child_set = set(shared_child_ids)
        leaders = [
            build_leader_column(pid, path, shelf_child_set)
            for pid in _sort_node_ids(by_id, parent_ids)
        ]
        child_trees: list[OrgChartNodeRead] = []
        for cid in _sort_node_ids(by_id, shared_child_ids):
            placed.add(cid)
            child_trees.append(build_regular(cid, path + (cid,)))
        pkey = "-".join(str(p) for p in _sort_node_ids(by_id, parent_ids))
        return OrgChartNodeRead(
            kind="leader_shelf",
            name="",
            position_label="",
            area_name="",
            leaders=leaders,
            children=child_trees,
            display_key=f"shelf-{pkey}",
        )

    def append_shelves_for_siblings(
        child_nodes: list[OrgChartNodeRead],
        sibling_ids: list[int],
        path: tuple[int, ...],
        used_in_shelf: set[int],
    ) -> None:
        sibling_set = set(sibling_ids)
        for pset_frozen, group_cids in sorted(
            shelf_by_parents.items(),
            key=lambda item: min(item[1]),
        ):
            if not set(pset_frozen).issubset(sibling_set):
                continue
            pending = [c for c in _sort_node_ids(by_id, group_cids) if c not in placed]
            if not pending:
                continue
            child_nodes.append(build_shelf(set(pset_frozen), pending, path))
            used_in_shelf.update(pset_frozen)

    def build_regular(nid: int, path: tuple[int, ...]) -> OrgChartNodeRead:
        n = by_id[nid]
        path_set = frozenset(path)
        child_nodes: list[OrgChartNodeRead] = []
        sibling_ids = children_of.get(nid, [])
        used_in_shelf: set[int] = set()

        append_shelves_for_siblings(child_nodes, sibling_ids, path + (nid,), used_in_shelf)

        for cid in _sort_node_ids(by_id, sibling_ids):
            if cid in path_set or cid in placed or cid in used_in_shelf:
                continue
            placed.add(cid)
            child_nodes.append(build_regular(cid, path + (cid,)))
        return _manual_node_read(n, child_nodes)

    roots_out: list[OrgChartNodeRead] = []
    for rid in root_ids:
        if rid in placed or rid in parents_in_shelf:
            continue
        placed.add(rid)
        roots_out.append(build_regular(rid, (rid,)))

    for pset_frozen, group_cids in sorted(
        shelf_by_parents.items(),
        key=lambda item: min(item[1]),
    ):
        pending = [c for c in _sort_node_ids(by_id, group_cids) if c not in placed]
        if not pending:
            continue
        pset = set(pset_frozen)
        boss_id = _shared_immediate_boss(pset, parents_map)
        if boss_id is not None and boss_id in by_id and not _node_in_forest(roots_out, boss_id):
            if boss_id not in placed:
                placed.add(boss_id)
            roots_out.append(
                _manual_node_read(by_id[boss_id], [build_shelf(pset, pending, (boss_id,))]),
            )
            continue
        if not all(_node_in_forest(roots_out, cid) for cid in pending):
            roots_out.append(build_shelf(pset, pending, ()))

    return roots_out


async def _load_nodes_and_edges(
    db: AsyncSession,
) -> tuple[list[OrgChartLayoutNode], list[OrgChartLayoutEdge]]:
    nr = await db.execute(
        select(OrgChartLayoutNode).order_by(OrgChartLayoutNode.sort_order, OrgChartLayoutNode.name)
    )
    er = await db.execute(select(OrgChartLayoutEdge))
    return list(nr.scalars().all()), list(er.scalars().all())


async def sync_employee_nodes(db: AsyncSession) -> None:
    """Crea/actualiza un nodo por cada empleado activo (base del organigrama)."""
    r = await db.execute(
        select(Employee)
        .options(selectinload(Employee.area))
        .order_by(Employee.name.asc())
    )
    employees = list(r.scalars().all())

    nr = await db.execute(select(OrgChartLayoutNode))
    existing = {n.employee_id: n for n in nr.scalars().all() if n.employee_id is not None}

    for emp in employees:
        area_name = emp.area.name if emp.area is not None else ""
        node = existing.get(emp.id)
        if node is None:
            db.add(
                OrgChartLayoutNode(
                    name=emp.name,
                    position_label=emp.position,
                    area_name=area_name,
                    employee_id=emp.id,
                )
            )
        else:
            node.name = emp.name
            node.position_label = emp.position
            node.area_name = area_name
    await db.flush()


async def get_manual_chart(db: AsyncSession) -> ManualOrgChartResponse:
    await sync_employee_nodes(db)
    nodes, edges = await _load_nodes_and_edges(db)
    roots = _build_display_roots(nodes, edges)

    parents = _parents_of(edges)
    unassigned = [
        OrgChartMemberRead(
            id=n.employee_id or n.id,
            name=n.name,
            position=n.position_label,
            area_name=n.area_name,
        )
        for n in nodes
        if n.id not in parents
    ]
    unassigned.sort(key=lambda x: x.name.lower())

    return ManualOrgChartResponse(
        nodes=[_node_to_read(n) for n in nodes],
        edges=[
            OrgChartLayoutEdgeRead(child_node_id=e.child_node_id, parent_node_id=e.parent_node_id)
            for e in edges
        ],
        roots=roots,
        unassigned=unassigned,
    )


async def _get_node(db: AsyncSession, node_id: int) -> OrgChartLayoutNode:
    r = await db.execute(select(OrgChartLayoutNode).where(OrgChartLayoutNode.id == node_id))
    node = r.scalar_one_or_none()
    if node is None:
        raise not_found("Nodo de organigrama no encontrado")
    return node


async def _validate_refs(
    db: AsyncSession,
    *,
    employee_id: int | None,
    user_id: int | None,
) -> None:
    if employee_id is not None:
        r = await db.execute(select(Employee.id).where(Employee.id == employee_id))
        if r.scalar_one_or_none() is None:
            raise not_found("Empleado no encontrado")
    if user_id is not None:
        r = await db.execute(select(User.id).where(User.id == user_id))
        if r.scalar_one_or_none() is None:
            raise not_found("Usuario no encontrado")


async def create_node(db: AsyncSession, data: OrgChartLayoutNodeCreate) -> OrgChartLayoutNode:
    await _validate_refs(db, employee_id=data.employee_id, user_id=data.user_id)
    if data.employee_id is not None:
        r = await db.execute(
            select(OrgChartLayoutNode.id).where(OrgChartLayoutNode.employee_id == data.employee_id)
        )
        if r.scalar_one_or_none() is not None:
            raise AppException(status_code=400, detail="Ese empleado ya tiene nodo en el organigrama")
    node = OrgChartLayoutNode(
        name=data.name.strip(),
        position_label=(data.position_label or "").strip(),
        area_name=(data.area_name or "").strip(),
        sort_order=data.sort_order,
        employee_id=data.employee_id,
        user_id=data.user_id,
    )
    db.add(node)
    await db.flush()
    return node


async def update_node(
    db: AsyncSession,
    node_id: int,
    data: OrgChartLayoutNodeUpdate,
) -> OrgChartLayoutNode:
    node = await _get_node(db, node_id)
    fields = data.model_dump(exclude_unset=True)
    if "employee_id" in fields or "user_id" in fields:
        await _validate_refs(
            db,
            employee_id=fields.get("employee_id", node.employee_id),
            user_id=fields.get("user_id", node.user_id),
        )
    for key, val in fields.items():
        if key == "name" and val is not None:
            setattr(node, key, val.strip())
        elif key in ("position_label", "area_name") and val is not None:
            setattr(node, key, val.strip())
        else:
            setattr(node, key, val)
    await db.flush()
    return node


async def delete_node(db: AsyncSession, node_id: int) -> None:
    await _get_node(db, node_id)
    await db.execute(delete(OrgChartLayoutNode).where(OrgChartLayoutNode.id == node_id))


async def add_edge(db: AsyncSession, child_node_id: int, parent_node_id: int) -> OrgChartLayoutEdge:
    if child_node_id == parent_node_id:
        raise AppException(status_code=400, detail="Una persona no puede reportarse a sí misma")
    await _get_node(db, child_node_id)
    await _get_node(db, parent_node_id)
    _, edges = await _load_nodes_and_edges(db)
    if any(e.child_node_id == child_node_id and e.parent_node_id == parent_node_id for e in edges):
        return OrgChartLayoutEdge(child_node_id=child_node_id, parent_node_id=parent_node_id)
    if _would_create_cycle(edges, child_id=child_node_id, parent_id=parent_node_id):
        raise AppException(status_code=400, detail="Esa relación crearía un ciclo en el organigrama")
    edge = OrgChartLayoutEdge(child_node_id=child_node_id, parent_node_id=parent_node_id)
    db.add(edge)
    await db.flush()
    return edge


async def remove_edge(db: AsyncSession, child_node_id: int, parent_node_id: int) -> None:
    await db.execute(
        delete(OrgChartLayoutEdge).where(
            OrgChartLayoutEdge.child_node_id == child_node_id,
            OrgChartLayoutEdge.parent_node_id == parent_node_id,
        )
    )


async def clear_edges(db: AsyncSession) -> None:
    await db.execute(delete(OrgChartLayoutEdge))
    nr = await db.execute(select(OrgChartLayoutNode))
    for n in nr.scalars().all():
        n.is_chart_root = False


async def pin_chart_root(db: AsyncSession, node_id: int) -> OrgChartLayoutNode:
    node = await _get_node(db, node_id)
    node.is_chart_root = True
    await db.flush()
    return node

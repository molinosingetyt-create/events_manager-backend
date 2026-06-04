from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, require_any_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.org_chart_layout import (
    ManualOrgChartResponse,
    OrgChartLayoutEdgeCreate,
    OrgChartLayoutEdgeRead,
    OrgChartLayoutNodeCreate,
    OrgChartLayoutNodeRead,
    OrgChartLayoutNodeUpdate,
)
from app.services import audit_service
from app.services import org_chart_layout_service as svc

router = APIRouter()


@router.get("/manual", response_model=ManualOrgChartResponse)
async def get_manual_org_chart(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.org_chart"))],
) -> ManualOrgChartResponse:
    data = await svc.get_manual_chart(db)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.view",
        entity_type="org_chart_layout",
        ip_address=client_ip(request),
    )
    await db.commit()
    return data


@router.post("/manual/nodes", response_model=OrgChartLayoutNodeRead)
async def create_manual_node(
    request: Request,
    body: OrgChartLayoutNodeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
) -> OrgChartLayoutNodeRead:
    node = await svc.create_node(db, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.create",
        entity_type="org_chart_layout",
        entity_id=node.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(node)
    return OrgChartLayoutNodeRead.model_validate(node)


@router.patch("/manual/nodes/{node_id}", response_model=OrgChartLayoutNodeRead)
async def update_manual_node(
    request: Request,
    node_id: int,
    body: OrgChartLayoutNodeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
) -> OrgChartLayoutNodeRead:
    node = await svc.update_node(db, node_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.update",
        entity_type="org_chart_layout",
        entity_id=node.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(node)
    return OrgChartLayoutNodeRead.model_validate(node)


@router.delete("/manual/nodes/{node_id}", status_code=204)
async def delete_manual_node(
    request: Request,
    node_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
) -> None:
    await svc.delete_node(db, node_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.delete",
        entity_type="org_chart_layout",
        entity_id=node_id,
        ip_address=client_ip(request),
    )
    await db.commit()


@router.post("/manual/edges", response_model=OrgChartLayoutEdgeRead)
async def add_manual_edge(
    request: Request,
    body: OrgChartLayoutEdgeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
) -> OrgChartLayoutEdgeRead:
    edge = await svc.add_edge(db, body.child_node_id, body.parent_node_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.edge_add",
        entity_type="org_chart_layout",
        entity_id=body.child_node_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return OrgChartLayoutEdgeRead(
        child_node_id=edge.child_node_id,
        parent_node_id=edge.parent_node_id,
    )


@router.delete("/manual/edges", status_code=204)
async def remove_manual_edge(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
    child_node_id: int = Query(...),
    parent_node_id: int = Query(...),
) -> None:
    await svc.remove_edge(db, child_node_id, parent_node_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.edge_remove",
        entity_type="org_chart_layout",
        entity_id=child_node_id,
        ip_address=client_ip(request),
    )
    await db.commit()


@router.post("/manual/nodes/{node_id}/pin-root", response_model=OrgChartLayoutNodeRead)
async def pin_manual_node_root(
    request: Request,
    node_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
) -> OrgChartLayoutNodeRead:
    node = await svc.pin_chart_root(db, node_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.pin_root",
        entity_type="org_chart_layout",
        entity_id=node.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(node)
    return OrgChartLayoutNodeRead.model_validate(node)


@router.post("/manual/reset-layout", response_model=ManualOrgChartResponse)
async def reset_manual_layout(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("org_chart.edit"))],
) -> ManualOrgChartResponse:
    """Borra todas las relaciones de reporte; mantiene el listado de empleados."""
    await svc.clear_edges(db)
    data = await svc.get_manual_chart(db)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="org_chart.manual.reset",
        entity_type="org_chart_layout",
        ip_address=client_ip(request),
    )
    await db.commit()
    return data

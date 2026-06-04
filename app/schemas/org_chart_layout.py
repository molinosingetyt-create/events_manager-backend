from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.employee import OrgChartMemberRead, OrgChartNodeRead


class OrgChartLayoutEdgeRead(BaseModel):
    child_node_id: int
    parent_node_id: int


class OrgChartLayoutNodeRead(BaseModel):
    id: int
    name: str
    position_label: str
    area_name: str = ""
    sort_order: int = 0
    is_chart_root: bool = False
    employee_id: Optional[int] = None
    user_id: Optional[int] = None

    model_config = {"from_attributes": True}


class OrgChartLayoutNodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    position_label: str = Field(default="", max_length=255)
    area_name: str = Field(default="", max_length=255)
    employee_id: Optional[int] = None
    user_id: Optional[int] = None
    sort_order: int = 0


class OrgChartLayoutNodeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    position_label: Optional[str] = Field(default=None, max_length=255)
    area_name: Optional[str] = Field(default=None, max_length=255)
    sort_order: Optional[int] = None
    is_chart_root: Optional[bool] = None
    employee_id: Optional[int] = None
    user_id: Optional[int] = None


class OrgChartLayoutEdgeCreate(BaseModel):
    child_node_id: int
    parent_node_id: int


class ManualOrgChartResponse(BaseModel):
    """Organigrama manual: todos los empleados como nodos + aristas de reporte."""

    nodes: list[OrgChartLayoutNodeRead]
    edges: list[OrgChartLayoutEdgeRead]
    roots: list[OrgChartNodeRead]
    unassigned: list[OrgChartMemberRead] = Field(
        default_factory=list,
        description="Nodos sin ningún líder asignado en el organigrama",
    )

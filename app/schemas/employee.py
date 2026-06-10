from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus


class EmployeeBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    identification_number: str = Field(min_length=1, max_length=64)
    position: str = Field(min_length=1, max_length=255)
    area_id: int
    leader_id: Optional[int] = None
    status: EntityStatus = EntityStatus.ACTIVE


class EmployeeCreate(EmployeeBase):
    temporal_category_id: int


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    identification_number: str | None = Field(default=None, min_length=1, max_length=64)
    position: str | None = Field(default=None, min_length=1, max_length=255)
    area_id: int | None = None
    leader_id: Optional[int] = None
    temporal_category_id: int | None = None
    status: EntityStatus | None = None


class EmployeeRead(BaseModel):
    id: int
    name: str
    identification_number: str
    position: str
    area_id: int
    area_name: str = ""
    leader_id: Optional[int]
    leader_name: Optional[str] = None
    temporal_category_id: int | None = None
    temporal_category_name: str = ""
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeProfileAccessRead(BaseModel):
    """Metadatos de acceso al expediente (fase 0); `expediente_available` en fase 1+."""

    employee_id: int
    view_level: Literal["basic", "full"]
    can_edit_profile: bool = False
    can_export: bool = False
    can_see_alerts: bool = False
    expediente_available: bool = True


class OrgChartMemberRead(BaseModel):
    """Colaborador bajo un líder (empleado)."""

    id: int
    name: str
    position: str
    area_name: str = ""


class OrgChartNodeRead(BaseModel):
    """Nodo recursivo del organigrama (grupo, usuario, empleado o manual)."""

    kind: Literal["group", "user", "employee", "manual", "leader_shelf"]
    user_id: int | None = None
    employee_id: int | None = None
    layout_node_id: int | None = None
    display_key: str | None = None
    name: str
    position_label: str
    area_name: str = ""
    children: list["OrgChartNodeRead"] = Field(default_factory=list)
    leaders: list["OrgChartNodeRead"] = Field(default_factory=list)


OrgChartNodeRead.model_rebuild()


class OrgChartTreeResponse(BaseModel):
    """Árbol único desde gerencia; `roots` suele tener un elemento o un grupo «Dirección»."""

    roots: list[OrgChartNodeRead]
    unassigned: list[OrgChartMemberRead]

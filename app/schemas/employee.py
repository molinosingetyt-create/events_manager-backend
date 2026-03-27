from datetime import datetime
from typing import Optional

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
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    identification_number: str | None = Field(default=None, min_length=1, max_length=64)
    position: str | None = Field(default=None, min_length=1, max_length=255)
    area_id: int | None = None
    leader_id: Optional[int] = None
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
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

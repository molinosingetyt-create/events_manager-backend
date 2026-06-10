from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus
from app.schemas.overtime import UserBriefRead


class ShiftScheduleCreate(BaseModel):
    employee_id: int
    shift_date: date
    start_time: time
    end_time: time
    notes: Optional[str] = Field(default=None, max_length=65535)
    status: EntityStatus = EntityStatus.ACTIVE


class ShiftScheduleUpdate(BaseModel):
    shift_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    notes: Optional[str] = Field(default=None, max_length=65535)
    status: EntityStatus | None = None


class ShiftScheduleRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str = ""
    created_by: int
    creator: UserBriefRead | None = None
    shift_date: date
    start_time: time
    end_time: time
    time_range_label: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

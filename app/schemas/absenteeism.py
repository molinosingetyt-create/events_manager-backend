from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import AbsenteeismClassification, EntityStatus
from app.schemas.overtime import UserBriefRead


class AbsenteeismRecordCreate(BaseModel):
    employee_id: int
    classification: AbsenteeismClassification
    start_date: date
    end_date: date
    justification: str = Field(min_length=1)
    status: EntityStatus = EntityStatus.ACTIVE


class AbsenteeismRecordUpdate(BaseModel):
    classification: AbsenteeismClassification | None = None
    start_date: date | None = None
    end_date: date | None = None
    justification: str | None = Field(default=None, min_length=1)
    status: EntityStatus | None = None


class AbsenteeismRecordRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str = ""
    created_by: int
    creator: UserBriefRead | None = None
    classification: str
    start_date: date
    end_date: date
    days: int
    justification: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

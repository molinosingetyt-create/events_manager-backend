from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus, IncapacityType
from app.schemas.overtime import UserBriefRead


class IncapacityHistoryRead(BaseModel):
    id: int
    incapacity_id: int
    action: str
    user_id: Optional[int]
    user: Optional[UserBriefRead] = None
    comment: Optional[str]
    snapshot: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class IncapacityNoteCreate(BaseModel):
    employee_id: int
    type: IncapacityType
    description: str = Field(min_length=1)
    support: Optional[str] = Field(default=None, max_length=65535)
    start_date: date
    end_date: Optional[date] = None
    status: EntityStatus = EntityStatus.ACTIVE


class IncapacityNoteUpdate(BaseModel):
    type: IncapacityType | None = None
    description: str | None = Field(default=None, min_length=1)
    support: Optional[str] = Field(default=None, max_length=65535)
    start_date: date | None = None
    end_date: Optional[date] = None
    status: EntityStatus | None = None


class IncapacityNoteRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str = ""
    type: str
    description: str
    support: Optional[str] = None
    start_date: date
    end_date: Optional[date]
    file_url: Optional[str]
    created_by: int
    creator: Optional[UserBriefRead] = None
    status: str
    created_at: datetime
    updated_at: datetime
    history: list[IncapacityHistoryRead] = []

    model_config = {"from_attributes": True}


class IncapacityCommentCreate(BaseModel):
    comment: str = Field(min_length=1)


class IncapacityCommentRead(BaseModel):
    id: int
    incapacity_id: int
    user_id: int
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}

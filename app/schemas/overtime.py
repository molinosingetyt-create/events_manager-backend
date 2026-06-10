from datetime import date as DateType
from datetime import datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserBriefRead(BaseModel):
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


class OvertimeRequestCreate(BaseModel):
    employee_id: int
    justification: str = Field(min_length=1)
    dates: list[DateType] = Field(min_length=1, max_length=31)
    start_time: time
    end_time: time

    @field_validator("dates")
    @classmethod
    def unique_dates(cls, v: list[DateType]) -> list[DateType]:
        if len(set(v)) != len(v):
            raise ValueError("No repita la misma fecha")
        return v


class OvertimeRequestUpdate(BaseModel):
    date: Optional[DateType] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    justification: str | None = Field(default=None, min_length=1)


class OvertimeApproveReject(BaseModel):
    approved: bool
    approval_comment: str | None = None


class OvertimeHistoryRead(BaseModel):
    id: int
    request_id: int
    action: str
    user_id: Optional[int]
    user: Optional[UserBriefRead] = None
    comment: Optional[str]
    snapshot: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OvertimeRequestRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    requested_by: int
    requester: UserBriefRead
    date: DateType
    hours: Decimal
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    time_range_label: Optional[str] = None
    justification: str
    status: str
    approved_by: Optional[int]
    approver: Optional[UserBriefRead] = None
    approval_comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    history: list[OvertimeHistoryRead] = []

    model_config = {"from_attributes": True}


class OvertimeBatchCreateRead(BaseModel):
    items: list[OvertimeRequestRead]
    hours_per_day: Decimal
    total_hours: Decimal

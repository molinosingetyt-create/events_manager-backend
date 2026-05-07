from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus, IncapacityType, LongAbsenceDocumentKind
from app.schemas.overtime import UserBriefRead


class IncapacityExtensionCreate(BaseModel):
    start_date: date
    end_date: date
    note: str = Field(min_length=1, max_length=65535)


class IncapacityExtensionRead(BaseModel):
    id: int
    incapacity_id: int
    start_date: date
    end_date: date
    file_url: str
    note: str
    created_by: int
    creator: Optional[UserBriefRead] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaderFilterOption(BaseModel):
    """Usuario con rol líder, para filtrar el listado de incapacidades por colaboradores."""

    id: int
    name: str


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
    temporal_category_id: int
    eps_arl_id: int | None = None
    diagnosis_id: int | None = None
    description: str = Field(min_length=1)
    support: Optional[str] = Field(default=None, max_length=65535)
    start_date: date
    end_date: Optional[date] = None
    status: EntityStatus = EntityStatus.ACTIVE
    long_absence_document_kind: LongAbsenceDocumentKind | None = None
    eps_transcribed_text: Optional[str] = Field(default=None, max_length=65535)  # ignorado; solo imagen EPS


class IncapacityNoteUpdate(BaseModel):
    type: IncapacityType | None = None
    temporal_category_id: int | None = None
    eps_arl_id: int | None = None
    diagnosis_id: int | None = None
    description: str | None = Field(default=None, min_length=1)
    support: Optional[str] = Field(default=None, max_length=65535)
    start_date: date | None = None
    end_date: Optional[date] = None
    status: EntityStatus | None = None
    long_absence_document_kind: LongAbsenceDocumentKind | None = None


class IncapacityNoteRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str = ""
    employee_identification: str = ""
    type: str
    temporal_category_id: int
    temporal_category_name: str = ""
    eps_arl_id: int | None = None
    eps_arl_label: str = ""
    diagnosis_id: int | None = None
    diagnosis_code: str = ""
    diagnosis_name: str = ""
    description: str
    support: Optional[str] = None
    start_date: date
    end_date: Optional[date]
    long_absence_document_kind: str | None = None
    file_url: Optional[str]
    long_absence_second_file_url: str | None = None
    long_absence_eps_transcribed_text: str | None = None
    created_by: int
    creator: Optional[UserBriefRead] = None
    status: str
    created_at: datetime
    updated_at: datetime
    history: list[IncapacityHistoryRead] = []
    extensions: list[IncapacityExtensionRead] = []

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

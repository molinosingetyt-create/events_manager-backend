from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EpsArlKind, EntityStatus


class TemporalCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    status: EntityStatus = EntityStatus.ACTIVE


class TemporalCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: EntityStatus | None = None


class TemporalCategoryRead(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EpsArlCreate(BaseModel):
    kind: EpsArlKind
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    status: EntityStatus = EntityStatus.ACTIVE


class EpsArlUpdate(BaseModel):
    kind: EpsArlKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    status: EntityStatus | None = None


class EpsArlRead(BaseModel):
    id: int
    kind: str
    name: str
    code: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiagnosisCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    description: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE


class DiagnosisUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    status: EntityStatus | None = None


class DiagnosisRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncapacityFormOptionsRead(BaseModel):
    temporal_categories: list[TemporalCategoryRead]
    eps_arl: list[EpsArlRead]
    diagnoses: list[DiagnosisRead]

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileBase(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    behavior_key: str = Field(min_length=1, max_length=32)


class ProfileCreate(ProfileBase):
    permission_ids: list[int] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    behavior_key: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = None


class ProfileRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    behavior_key: str
    is_system: bool
    sort_order: int
    permission_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfilePermissionsUpdate(BaseModel):
    permission_ids: list[int] = Field(default_factory=list)

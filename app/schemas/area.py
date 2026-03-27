from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus


class AreaBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    status: EntityStatus = EntityStatus.ACTIVE


class AreaCreate(AreaBase):
    pass


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: EntityStatus | None = None


class AreaRead(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

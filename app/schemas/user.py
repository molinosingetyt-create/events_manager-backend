from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import EntityStatus


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    role: str = Field(min_length=1, max_length=64, description="Código de perfil (p. ej. ADMIN, HR)")
    area_id: int
    status: EntityStatus = EntityStatus.ACTIVE


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, min_length=1, max_length=64)
    area_id: int | None = None
    status: EntityStatus | None = None


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    role: str
    area_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[a-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class PermissionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None


class PermissionBrief(BaseModel):
    """Código técnico + nombre visible (p. ej. perfil de usuario)."""

    code: str
    name: str


class PermissionRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

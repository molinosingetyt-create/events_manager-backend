from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    id: int
    kind: str
    message: str
    overtime_request_id: Optional[int] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    payload: Optional[dict[str, Any]] = None


class UnreadCountResponse(BaseModel):
    count: int = Field(ge=0)

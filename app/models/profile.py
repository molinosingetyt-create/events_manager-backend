from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Table, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User

profile_permissions = Table(
    "profile_permissions",
    Base.metadata,
    Column("profile_id", ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    behavior_key: Mapped[str] = mapped_column(String(32), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=profile_permissions,
        back_populates="profiles",
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="profile")

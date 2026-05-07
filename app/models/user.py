from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.app_notification import AppNotification
    from app.models.area import Area
    from app.models.employee import Employee
    from app.models.profile import Profile


class User(Base, TimestampMixin, StatusMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)

    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False)

    profile: Mapped["Profile"] = relationship("Profile", back_populates="users")
    area: Mapped["Area"] = relationship("Area", back_populates="users")
    led_employees: Mapped[list["Employee"]] = relationship(
        "Employee", foreign_keys="Employee.leader_id", back_populates="leader_user"
    )
    notifications: Mapped[list["AppNotification"]] = relationship(
        "AppNotification", back_populates="user", cascade="all, delete-orphan"
    )

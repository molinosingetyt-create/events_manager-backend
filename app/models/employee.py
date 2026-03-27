from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.incapacity import IncapacityNote
    from app.models.overtime import OvertimeRequest
    from app.models.user import User


class Employee(Base, TimestampMixin, StatusMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identification_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    position: Mapped[str] = mapped_column(String(255), nullable=False)

    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False)
    leader_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    area: Mapped["Area"] = relationship("Area", back_populates="employees")
    leader_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[leader_id], back_populates="led_employees"
    )
    overtime_requests: Mapped[list["OvertimeRequest"]] = relationship(
        "OvertimeRequest", back_populates="employee"
    )
    incapacity_notes: Mapped[list["IncapacityNote"]] = relationship(
        "IncapacityNote", back_populates="employee"
    )

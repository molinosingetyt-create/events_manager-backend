from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class Area(Base, TimestampMixin, StatusMixin):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="area")
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="area")

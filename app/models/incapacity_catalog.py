from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import StatusMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.incapacity import IncapacityNote


class TemporalCategory(Base, TimestampMixin, StatusMixin):
    """Categoría de temporal (definida por administración)."""

    __tablename__ = "temporal_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_temporal_categories_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    incapacity_notes: Mapped[list["IncapacityNote"]] = relationship(
        "IncapacityNote", back_populates="temporal_category"
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="temporal_category"
    )


class EpsArlEntity(Base, TimestampMixin, StatusMixin):
    """Entidad EPS o ARL."""

    __tablename__ = "eps_arl_entities"
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_eps_arl_kind_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # eps | arl
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    incapacity_notes: Mapped[list["IncapacityNote"]] = relationship(
        "IncapacityNote", back_populates="eps_arl"
    )


class Diagnosis(Base, TimestampMixin, StatusMixin):
    """Diagnóstico médico (código CIE u otro)."""

    __tablename__ = "diagnoses"
    __table_args__ = (UniqueConstraint("code", name="uq_diagnoses_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    incapacity_notes: Mapped[list["IncapacityNote"]] = relationship(
        "IncapacityNote", back_populates="diagnosis"
    )

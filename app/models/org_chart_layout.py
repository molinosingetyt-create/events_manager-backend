from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class OrgChartLayoutNode(Base, TimestampMixin):
    """Nodo del organigrama manual (un empleado = un nodo; líderes vía aristas)."""

    __tablename__ = "org_chart_layout_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    area_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_chart_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    employee: Mapped[Optional["Employee"]] = relationship("Employee")
    user: Mapped[Optional["User"]] = relationship("User")
    leader_edges: Mapped[list["OrgChartLayoutEdge"]] = relationship(
        "OrgChartLayoutEdge",
        foreign_keys="OrgChartLayoutEdge.child_node_id",
        back_populates="child_node",
        cascade="all, delete-orphan",
    )


class OrgChartLayoutEdge(Base):
    """El hijo (child) reporta al padre (parent). Varios padres permitidos."""

    __tablename__ = "org_chart_layout_edges"
    __table_args__ = (
        UniqueConstraint("child_node_id", "parent_node_id", name="uq_org_chart_layout_edge"),
    )

    child_node_id: Mapped[int] = mapped_column(
        ForeignKey("org_chart_layout_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    parent_node_id: Mapped[int] = mapped_column(
        ForeignKey("org_chart_layout_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    child_node: Mapped["OrgChartLayoutNode"] = relationship(
        "OrgChartLayoutNode",
        foreign_keys=[child_node_id],
        back_populates="leader_edges",
    )
    parent_node: Mapped["OrgChartLayoutNode"] = relationship(
        "OrgChartLayoutNode",
        foreign_keys=[parent_node_id],
    )

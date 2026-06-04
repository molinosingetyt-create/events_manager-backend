"""Organigrama manual (tabla independiente de empleados)

Revision ID: 015
Revises: 014
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def upgrade() -> None:
    if not _table_exists("org_chart_layout_nodes"):
        op.create_table(
            "org_chart_layout_nodes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("position_label", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("area_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("employee_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["parent_id"], ["org_chart_layout_nodes.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        if not _index_exists("org_chart_layout_nodes", "ix_org_chart_layout_nodes_parent_id"):
            op.create_index(
                "ix_org_chart_layout_nodes_parent_id", "org_chart_layout_nodes", ["parent_id"]
            )
        if not _index_exists("org_chart_layout_nodes", "ix_org_chart_layout_nodes_employee_id"):
            op.create_index(
                "ix_org_chart_layout_nodes_employee_id", "org_chart_layout_nodes", ["employee_id"]
            )
        if not _index_exists("org_chart_layout_nodes", "ix_org_chart_layout_nodes_user_id"):
            op.create_index(
                "ix_org_chart_layout_nodes_user_id", "org_chart_layout_nodes", ["user_id"]
            )

    conn = op.get_bind()
    conn.execute(
        text(
            """
            INSERT INTO permissions (code, name, description, is_system, sort_order)
            SELECT
                'org_chart.edit',
                'Editar organigrama manual',
                'Crear y reorganizar el organigrama sin modificar empleados',
                true,
                47
            WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'org_chart.edit')
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id)
            SELECT p.id, m.id
            FROM profiles p
            CROSS JOIN (SELECT id FROM permissions WHERE code = 'org_chart.edit') AS m
            WHERE p.code IN ('ADMIN', 'HR', 'MANAGEMENT')
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            DELETE FROM profile_permissions
            WHERE permission_id = (SELECT id FROM permissions WHERE code = 'org_chart.edit')
            """
        )
    )
    conn.execute(text("DELETE FROM permissions WHERE code = 'org_chart.edit'"))
    if _table_exists("org_chart_layout_nodes"):
        if _index_exists("org_chart_layout_nodes", "ix_org_chart_layout_nodes_user_id"):
            op.drop_index("ix_org_chart_layout_nodes_user_id", table_name="org_chart_layout_nodes")
        if _index_exists("org_chart_layout_nodes", "ix_org_chart_layout_nodes_employee_id"):
            op.drop_index(
                "ix_org_chart_layout_nodes_employee_id", table_name="org_chart_layout_nodes"
            )
        if _index_exists("org_chart_layout_nodes", "ix_org_chart_layout_nodes_parent_id"):
            op.drop_index("ix_org_chart_layout_nodes_parent_id", table_name="org_chart_layout_nodes")
        op.drop_table("org_chart_layout_nodes")

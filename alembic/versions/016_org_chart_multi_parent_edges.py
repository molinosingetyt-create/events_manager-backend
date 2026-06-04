"""Organigrama manual: varios líderes por persona (aristas)

Revision ID: 016
Revises: 015
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def _unique_exists(table: str, name: str) -> bool:
    bind = op.get_bind()
    return name in {u["name"] for u in inspect(bind).get_unique_constraints(table)}


def _fk_exists(table: str, fk_name: str) -> bool:
    bind = op.get_bind()
    return fk_name in {fk["name"] for fk in inspect(bind).get_foreign_keys(table)}


def upgrade() -> None:
    if not _table_exists("org_chart_layout_edges"):
        op.create_table(
            "org_chart_layout_edges",
            sa.Column("child_node_id", sa.Integer(), nullable=False),
            sa.Column("parent_node_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["child_node_id"], ["org_chart_layout_nodes.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["parent_node_id"], ["org_chart_layout_nodes.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("child_node_id", "parent_node_id"),
        )

    if _column_exists("org_chart_layout_nodes", "parent_id"):
        conn = op.get_bind()
        conn.execute(
            sa.text(
                """
                INSERT INTO org_chart_layout_edges (child_node_id, parent_node_id)
                SELECT id, parent_id FROM org_chart_layout_nodes
                WHERE parent_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM org_chart_layout_edges e
                    WHERE e.child_node_id = org_chart_layout_nodes.id
                      AND e.parent_node_id = org_chart_layout_nodes.parent_id
                )
                """
            )
        )
        if _index_exists_nodes_parent():
            op.drop_index("ix_org_chart_layout_nodes_parent_id", table_name="org_chart_layout_nodes")
        if _fk_exists("org_chart_layout_nodes", "org_chart_layout_nodes_parent_id_fkey"):
            op.drop_constraint(
                "org_chart_layout_nodes_parent_id_fkey",
                "org_chart_layout_nodes",
                type_="foreignkey",
            )
        op.drop_column("org_chart_layout_nodes", "parent_id")

    if not _unique_exists("org_chart_layout_nodes", "uq_org_chart_layout_nodes_employee_id"):
        op.create_unique_constraint(
            "uq_org_chart_layout_nodes_employee_id",
            "org_chart_layout_nodes",
            ["employee_id"],
        )

    if not _column_exists("org_chart_layout_nodes", "is_chart_root"):
        op.add_column(
            "org_chart_layout_nodes",
            sa.Column("is_chart_root", sa.Boolean(), nullable=False, server_default="false"),
        )


def _index_exists_nodes_parent() -> bool:
    bind = op.get_bind()
    return "ix_org_chart_layout_nodes_parent_id" in {
        idx["name"] for idx in inspect(bind).get_indexes("org_chart_layout_nodes")
    }


def downgrade() -> None:
    if not _column_exists("org_chart_layout_nodes", "parent_id"):
        op.add_column("org_chart_layout_nodes", sa.Column("parent_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "org_chart_layout_nodes_parent_id_fkey",
            "org_chart_layout_nodes",
            "org_chart_layout_nodes",
            ["parent_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index("ix_org_chart_layout_nodes_parent_id", "org_chart_layout_nodes", ["parent_id"])

    if _table_exists("org_chart_layout_edges"):
        conn = op.get_bind()
        conn.execute(
            sa.text(
                """
                UPDATE org_chart_layout_nodes n
                SET parent_id = (
                    SELECT e.parent_node_id FROM org_chart_layout_edges e
                    WHERE e.child_node_id = n.id
                    LIMIT 1
                )
                WHERE parent_id IS NULL
                """
            )
        )

    if _column_exists("org_chart_layout_nodes", "is_chart_root"):
        op.drop_column("org_chart_layout_nodes", "is_chart_root")
    if _unique_exists("org_chart_layout_nodes", "uq_org_chart_layout_nodes_employee_id"):
        op.drop_constraint(
            "uq_org_chart_layout_nodes_employee_id", "org_chart_layout_nodes", type_="unique"
        )
    if _table_exists("org_chart_layout_edges"):
        op.drop_table("org_chart_layout_edges")

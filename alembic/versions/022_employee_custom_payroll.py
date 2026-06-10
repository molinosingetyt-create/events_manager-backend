"""Campos personalizados y nómina (fase 6)

Revision ID: 022
Revises: 021
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = [
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
]

NEW_PERMS = [
    ("employees.profile.custom_fields.manage", "Configurar campos personalizados del expediente", 51),
    ("employees.profile.payroll", "Gestionar novedades de nómina en expediente", 52),
]

PERM_BY_PROFILE = {
    "ADMIN": [
        "employees.profile.custom_fields.manage",
        "employees.profile.payroll",
    ],
    "HR": [
        "employees.profile.custom_fields.manage",
        "employees.profile.payroll",
    ],
    "MANAGEMENT": [],
    "LEADER": [],
}


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not _table_exists(table):
        return False
    return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def upgrade() -> None:
    if not _table_exists("employee_custom_field_defs"):
        op.create_table(
            "employee_custom_field_defs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("field_key", sa.String(length=64), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("field_type", sa.String(length=32), nullable=False, server_default="text"),
            sa.Column("section", sa.String(length=128), nullable=True),
            sa.Column("options_json", sa.Text(), nullable=True),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            *_TS,
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("field_key", name="uq_employee_custom_field_defs_field_key"),
        )

    if not _table_exists("employee_custom_field_values"):
        op.create_table(
            "employee_custom_field_values",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("field_def_id", sa.Integer(), nullable=False),
            sa.Column("value_text", sa.Text(), nullable=True),
            *_TS,
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["field_def_id"], ["employee_custom_field_defs.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "employee_id",
                "field_def_id",
                name="uq_employee_custom_field_values_emp_field",
            ),
        )
    if not _index_exists("employee_custom_field_values", "ix_employee_custom_field_values_employee_id"):
        op.create_index(
            "ix_employee_custom_field_values_employee_id",
            "employee_custom_field_values",
            ["employee_id"],
        )

    if not _table_exists("employee_payroll_entries"):
        op.create_table(
            "employee_payroll_entries",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("period_month", sa.Date(), nullable=False),
            sa.Column("concept_type", sa.String(length=64), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=False),
            sa.Column("amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("reference_code", sa.String(length=64), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            *_TS,
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("employee_payroll_entries", "ix_employee_payroll_entries_employee_id"):
        op.create_index(
            "ix_employee_payroll_entries_employee_id",
            "employee_payroll_entries",
            ["employee_id"],
        )

    conn = op.get_bind()
    for code, name, sort_order in NEW_PERMS:
        conn.execute(
            text(
                """
                INSERT INTO permissions (code, name, description, is_system, sort_order)
                SELECT :code, :name, NULL, true, :so
                WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = :code)
                """
            ),
            {"code": code, "name": name, "so": sort_order},
        )
    for profile_code, codes in PERM_BY_PROFILE.items():
        for perm_code in codes:
            conn.execute(
                text(
                    """
                    INSERT INTO profile_permissions (profile_id, permission_id)
                    SELECT p.id, m.id
                    FROM profiles p
                    CROSS JOIN (SELECT id FROM permissions WHERE code = :perm) AS m
                    WHERE p.code = :profile
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"profile": profile_code, "perm": perm_code},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for code, _, _ in NEW_PERMS:
        conn.execute(
            text(
                """
                DELETE FROM profile_permissions
                WHERE permission_id = (SELECT id FROM permissions WHERE code = :code)
                """
            ),
            {"code": code},
        )
        conn.execute(text("DELETE FROM permissions WHERE code = :code"), {"code": code})

    for table in (
        "employee_payroll_entries",
        "employee_custom_field_values",
        "employee_custom_field_defs",
    ):
        idx = f"ix_{table}_employee_id"
        if _index_exists(table, idx):
            op.drop_index(idx, table_name=table)
        if _table_exists(table):
            op.drop_table(table)

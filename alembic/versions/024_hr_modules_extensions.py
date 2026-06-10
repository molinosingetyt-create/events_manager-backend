"""Incapacidad quincena, módulos ausentismo y turnos

Revision ID: 024
Revises: 023
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "024"
down_revision: Union[str, None] = "023"
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

_NEW_PERMS = [
    ("absenteeism.view", "Ver ausentismo", 50),
    ("absenteeism.create", "Registrar ausentismo", 51),
    ("absenteeism.edit", "Editar ausentismo", 52),
    ("absenteeism.delete", "Eliminar ausentismo", 53),
    ("shifts.view", "Ver programación de turnos", 54),
    ("shifts.create", "Crear turnos programados", 55),
    ("shifts.edit", "Editar turnos programados", 56),
    ("shifts.delete", "Eliminar turnos programados", 57),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if "incapacity_notes" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("incapacity_notes")}
        if "causation_year" not in cols:
            op.add_column("incapacity_notes", sa.Column("causation_year", sa.Integer(), nullable=True))
        if "causation_month" not in cols:
            op.add_column("incapacity_notes", sa.Column("causation_month", sa.Integer(), nullable=True))
        if "causation_half" not in cols:
            op.add_column("incapacity_notes", sa.Column("causation_half", sa.Integer(), nullable=True))

    if "absenteeism_records" not in insp.get_table_names():
        op.create_table(
            "absenteeism_records",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("classification", sa.String(length=32), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("days", sa.Integer(), nullable=False),
            sa.Column("justification", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            *_TS,
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_absenteeism_records_employee_id", "absenteeism_records", ["employee_id"])
        op.create_index("ix_absenteeism_records_start_date", "absenteeism_records", ["start_date"])

    if "shift_schedules" not in insp.get_table_names():
        op.create_table(
            "shift_schedules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("shift_date", sa.Date(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            *_TS,
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_shift_schedules_employee_id", "shift_schedules", ["employee_id"])
        op.create_index("ix_shift_schedules_shift_date", "shift_schedules", ["shift_date"])

    conn = op.get_bind()
    for code, name, sort_order in _NEW_PERMS:
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
    conn.execute(
        text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id)
            SELECT p.id, m.id
            FROM profiles p
            CROSS JOIN permissions m
            WHERE p.code = 'ADMIN'
              AND (m.code LIKE 'absenteeism.%' OR m.code LIKE 'shifts.%')
            ON CONFLICT (profile_id, permission_id) DO NOTHING
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id)
            SELECT p.id, m.id
            FROM profiles p
            JOIN permissions m ON m.code IN (
                'absenteeism.view','absenteeism.create','absenteeism.edit',
                'shifts.view','shifts.create','shifts.edit'
            )
            WHERE p.code IN ('HR', 'MANAGEMENT', 'LEADER')
            ON CONFLICT (profile_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    conn = op.get_bind()
    for code, _, _ in reversed(_NEW_PERMS):
        conn.execute(
            text(
                """
                DELETE FROM profile_permissions
                WHERE permission_id IN (SELECT id FROM permissions WHERE code = :code)
                """
            ),
            {"code": code},
        )
        conn.execute(text("DELETE FROM permissions WHERE code = :code"), {"code": code})
    if "shift_schedules" in insp.get_table_names():
        op.drop_table("shift_schedules")
    if "absenteeism_records" in insp.get_table_names():
        op.drop_table("absenteeism_records")
    cols = {c["name"] for c in insp.get_columns("incapacity_notes")} if "incapacity_notes" in insp.get_table_names() else set()
    if "causation_half" in cols:
        op.drop_column("incapacity_notes", "causation_half")
    if "causation_month" in cols:
        op.drop_column("incapacity_notes", "causation_month")
    if "causation_year" in cols:
        op.drop_column("incapacity_notes", "causation_year")

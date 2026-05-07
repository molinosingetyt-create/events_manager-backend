"""incapacity_extensions table + permiso prórroga para todos los perfiles

Revision ID: 012
Revises: 011
Create Date: 2026-04-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    idx_name = op.f("ix_incapacity_extensions_incapacity_id")

    if "incapacity_extensions" not in insp.get_table_names():
        op.create_table(
            "incapacity_extensions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("incapacity_id", sa.Integer(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("file_url", sa.String(length=1024), nullable=False),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["incapacity_id"], ["incapacity_notes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            idx_name,
            "incapacity_extensions",
            ["incapacity_id"],
            unique=False,
        )
    else:
        existing_ix = {i["name"] for i in insp.get_indexes("incapacity_extensions")}
        if idx_name not in existing_ix:
            op.create_index(
                idx_name,
                "incapacity_extensions",
                ["incapacity_id"],
                unique=False,
            )

    conn = op.get_bind()
    conn.execute(
        text(
            """
            INSERT INTO permissions (code, name, description, is_system, sort_order)
            SELECT
                'incapacity.extension',
                'Prórroga de incapacidad',
                'Registrar prórroga asociada a una incapacidad',
                true,
                45
            WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'incapacity.extension')
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id)
            SELECT p.id, m.id
            FROM profiles p
            CROSS JOIN (SELECT id FROM permissions WHERE code = 'incapacity.extension') AS m
            ON CONFLICT (profile_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            DELETE FROM profile_permissions
            WHERE permission_id = (SELECT id FROM permissions WHERE code = 'incapacity.extension')
            """
        )
    )
    conn.execute(text("DELETE FROM permissions WHERE code = 'incapacity.extension'"))
    op.drop_index(op.f("ix_incapacity_extensions_incapacity_id"), table_name="incapacity_extensions")
    op.drop_table("incapacity_extensions")

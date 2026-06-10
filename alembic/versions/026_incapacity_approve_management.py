"""Asignar incapacity.approve al perfil Gerencia (comportamiento previo por rol)

Revision ID: 026
Revises: 025
Create Date: 2026-06-10

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id)
            SELECT p.id, m.id
            FROM profiles p
            CROSS JOIN (SELECT id FROM permissions WHERE code = 'incapacity.approve') AS m
            WHERE p.code = 'MANAGEMENT'
              AND m.id IS NOT NULL
            ON CONFLICT (profile_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            DELETE FROM profile_permissions pp
            USING profiles p, permissions m
            WHERE pp.profile_id = p.id
              AND pp.permission_id = m.id
              AND p.code = 'MANAGEMENT'
              AND m.code = 'incapacity.approve'
            """
        )
    )

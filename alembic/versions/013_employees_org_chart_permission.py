"""Permiso organigrama (solo admin, RRHH y gerencia)

Revision ID: 013
Revises: 012
Create Date: 2026-05-13

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            INSERT INTO permissions (code, name, description, is_system, sort_order)
            SELECT
                'employees.org_chart',
                'Ver organigrama',
                'Estructura de líderes y colaboradores (administración, gerencia y RRHH)',
                true,
                46
            WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'employees.org_chart')
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id)
            SELECT p.id, m.id
            FROM profiles p
            CROSS JOIN (SELECT id FROM permissions WHERE code = 'employees.org_chart') AS m
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
            WHERE permission_id = (SELECT id FROM permissions WHERE code = 'employees.org_chart')
            """
        )
    )
    conn.execute(text("DELETE FROM permissions WHERE code = 'employees.org_chart'"))

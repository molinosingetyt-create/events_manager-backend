"""Permisos expediente HR (fase 0: visibilidad por perfil)

Revision ID: 017
Revises: 016
Create Date: 2026-06-03

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_PERMS = [
    ("employees.profile.full", "Ver expediente HR completo", 47),
    ("employees.profile.edit", "Editar expediente HR", 48),
    ("employees.profile.export", "Exportar expediente HR (PDF / Excel)", 49),
    ("employees.profile.alerts", "Alertas de expediente HR", 50),
]

PROFILE_BY_PROFILE = {
    "ADMIN": [
        "employees.profile.full",
        "employees.profile.edit",
        "employees.profile.export",
        "employees.profile.alerts",
    ],
    "HR": [
        "employees.profile.full",
        "employees.profile.edit",
        "employees.profile.export",
        "employees.profile.alerts",
    ],
    "MANAGEMENT": [
        "employees.profile.full",
        "employees.profile.export",
        "employees.profile.alerts",
    ],
    "LEADER": [],
}


def upgrade() -> None:
    conn = op.get_bind()
    for code, name, sort_order in PROFILE_PERMS:
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

    for profile_code, codes in PROFILE_BY_PROFILE.items():
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
    codes = [p[0] for p in PROFILE_PERMS]
    for code in codes:
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

"""Repara instalaciones donde 006 quedó aplicada sin users.profile_id (guard antiguo defectuoso).

Revision ID: 007
Revises: 006
Create Date: 2026-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("users.view", "Ver usuarios"),
    ("users.create", "Crear usuarios"),
    ("users.edit", "Editar usuarios"),
    ("users.delete", "Eliminar / desactivar usuarios"),
    ("employees.view", "Ver empleados"),
    ("employees.create", "Crear empleados"),
    ("employees.edit", "Editar empleados"),
    ("employees.delete", "Eliminar empleados"),
    ("areas.view", "Ver áreas"),
    ("areas.create", "Crear áreas"),
    ("areas.edit", "Editar áreas"),
    ("areas.delete", "Eliminar áreas"),
    ("overtime.view", "Ver horas extra"),
    ("overtime.create", "Crear solicitudes de horas extra"),
    ("overtime.edit", "Editar horas extra"),
    ("overtime.delete", "Eliminar horas extra"),
    ("overtime.approve", "Aprobar / rechazar horas extra"),
    ("incapacity.view", "Ver incapacidades y notas"),
    ("incapacity.create", "Crear incapacidades / notas"),
    ("incapacity.edit", "Editar incapacidades / notas"),
    ("incapacity.delete", "Eliminar incapacidades / notas"),
    ("incapacity.approve", "Aprobar / rechazar incapacidades"),
    ("catalog.settings", "Catálogos (temporal, EPS/ARL, diagnósticos)"),
    ("security.profiles", "Administrar perfiles"),
    ("security.permissions", "Administrar permisos"),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "profile_id" in user_cols:
        return

    tables = set(insp.get_table_names())

    if "permissions" not in tables:
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=96), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    if "profiles" not in tables:
        op.create_table(
            "profiles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("behavior_key", sa.String(length=32), nullable=False),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    if "profile_permissions" not in inspect(bind).get_table_names():
        op.create_table(
            "profile_permissions",
            sa.Column("profile_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("profile_id", "permission_id"),
        )

    conn = op.get_bind()
    perm_count = conn.execute(text("SELECT COUNT(*) FROM permissions")).scalar_one()
    if int(perm_count) == 0:
        for i, (code, name) in enumerate(PERMISSIONS):
            conn.execute(
                text(
                    """
                    INSERT INTO permissions (code, name, description, is_system, sort_order)
                    VALUES (:code, :name, NULL, true, :so)
                    """
                ),
                {"code": code, "name": name, "so": i},
            )

    prof_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar_one()
    if int(prof_count) == 0:
        profiles_seed = [
            ("ADMIN", "Administrador", "Acceso completo y catálogos", "ADMIN"),
            ("HR", "Recursos humanos", "Gestión de personas y registros", "HR"),
            ("MANAGEMENT", "Gerencia", "Aprobaciones y visión global", "MANAGEMENT"),
            ("LEADER", "Líder", "Equipo y área asignada", "LEADER"),
        ]
        for i, (code, name, desc, bk) in enumerate(profiles_seed):
            conn.execute(
                text(
                    """
                    INSERT INTO profiles (code, name, description, behavior_key, is_system, sort_order)
                    VALUES (:code, :name, :desc, :bk, true, :so)
                    """
                ),
                {"code": code, "name": name, "desc": desc, "bk": bk, "so": i},
            )

    pp_count = conn.execute(text("SELECT COUNT(*) FROM profile_permissions")).scalar_one()
    if int(pp_count) == 0:
        all_codes = [p[0] for p in PERMISSIONS]
        admin_codes = all_codes
        hr_codes = [
            c
            for c in all_codes
            if c
            not in (
                "overtime.approve",
                "incapacity.approve",
                "catalog.settings",
                "security.profiles",
                "security.permissions",
            )
        ]
        mgmt_codes = [
            "users.view",
            "employees.view",
            "overtime.view",
            "overtime.create",
            "overtime.edit",
            "overtime.approve",
            "incapacity.view",
            "incapacity.create",
            "incapacity.edit",
        ]
        leader_codes = [
            "employees.view",
            "overtime.view",
            "overtime.create",
            "overtime.edit",
            "incapacity.view",
            "incapacity.create",
            "incapacity.edit",
        ]
        for profile_code, codes in [
            ("ADMIN", admin_codes),
            ("HR", hr_codes),
            ("MANAGEMENT", mgmt_codes),
            ("LEADER", leader_codes),
        ]:
            pid = conn.execute(text("SELECT id FROM profiles WHERE code = :c"), {"c": profile_code}).scalar_one()
            for perm_code in codes:
                rid = conn.execute(
                    text("SELECT id FROM permissions WHERE code = :c"),
                    {"c": perm_code},
                ).scalar_one_or_none()
                if rid is None:
                    continue
                conn.execute(
                    text("INSERT INTO profile_permissions (profile_id, permission_id) VALUES (:p, :m)"),
                    {"p": pid, "m": rid},
                )

    role_len = conn.execute(
        text(
            """
            SELECT character_maximum_length FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'role'
            """
        )
    ).scalar_one_or_none()
    if role_len is not None and int(role_len) < 64:
        op.alter_column(
            "users",
            "role",
            existing_type=sa.String(length=int(role_len)),
            type_=sa.String(length=64),
            existing_nullable=False,
        )

    op.add_column("users", sa.Column("profile_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_profile_id", "users", "profiles", ["profile_id"], ["id"], ondelete="RESTRICT")

    conn.execute(
        text(
            """
            UPDATE users u
            SET profile_id = p.id
            FROM profiles p
            WHERE u.role = p.code
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE users
            SET profile_id = (SELECT id FROM profiles WHERE code = 'LEADER' LIMIT 1)
            WHERE profile_id IS NULL
            """
        )
    )
    op.alter_column("users", "profile_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "profile_id" not in user_cols:
        return
    op.drop_constraint("fk_users_profile_id", "users", type_="foreignkey")
    op.drop_column("users", "profile_id")

"""profiles, permissions, profile_permissions; users.profile_id

Revision ID: 006
Revises: 005
Create Date: 2026-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

from app.db.rbac_seed import seed_rbac_sync

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "permissions" in tables:
        perm_count = bind.execute(text("SELECT COUNT(*) FROM permissions")).scalar() or 0
        if perm_count > 0:
            return
        # Tablas creadas por create_all (p. ej.) pero sin datos RBAC
        seed_rbac_sync(bind)
        return

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

    op.create_table(
        "profile_permissions",
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id", "permission_id"),
    )

    conn = op.get_bind()
    seed_rbac_sync(conn)

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=32),
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
    if "permissions" not in insp.get_table_names():
        return

    op.drop_constraint("fk_users_profile_id", "users", type_="foreignkey")
    op.drop_column("users", "profile_id")
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.drop_table("profile_permissions")
    op.drop_table("profiles")
    op.drop_table("permissions")

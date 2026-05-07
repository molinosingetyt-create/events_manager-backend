"""incapacity catalogs: temporal, eps/arl, diagnoses

Revision ID: 005
Revises: 004
Create Date: 2026-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "temporal_categories" in insp.get_table_names():
        return

    op.create_table(
        "temporal_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_temporal_categories_name"),
    )
    op.create_table(
        "eps_arl_entities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "name", name="uq_eps_arl_kind_name"),
    )
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_diagnoses_code"),
    )

    op.execute(
        text(
            """
            INSERT INTO temporal_categories (name, status, created_at, updated_at)
            VALUES ('Sin clasificar', 'active', NOW(), NOW())
            """
        )
    )

    op.add_column("incapacity_notes", sa.Column("temporal_category_id", sa.Integer(), nullable=True))
    op.add_column("incapacity_notes", sa.Column("eps_arl_id", sa.Integer(), nullable=True))
    op.add_column("incapacity_notes", sa.Column("diagnosis_id", sa.Integer(), nullable=True))

    op.execute(
        text(
            """
            UPDATE incapacity_notes
            SET temporal_category_id = (SELECT id FROM temporal_categories ORDER BY id ASC LIMIT 1)
            WHERE temporal_category_id IS NULL
            """
        )
    )

    op.alter_column("incapacity_notes", "temporal_category_id", existing_type=sa.Integer(), nullable=False)

    op.create_foreign_key(
        "fk_incapacity_notes_temporal_category_id",
        "incapacity_notes",
        "temporal_categories",
        ["temporal_category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_incapacity_notes_eps_arl_id",
        "incapacity_notes",
        "eps_arl_entities",
        ["eps_arl_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_incapacity_notes_diagnosis_id",
        "incapacity_notes",
        "diagnoses",
        ["diagnosis_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_incapacity_notes_diagnosis_id", "incapacity_notes", type_="foreignkey")
    op.drop_constraint("fk_incapacity_notes_eps_arl_id", "incapacity_notes", type_="foreignkey")
    op.drop_constraint("fk_incapacity_notes_temporal_category_id", "incapacity_notes", type_="foreignkey")
    op.drop_column("incapacity_notes", "diagnosis_id")
    op.drop_column("incapacity_notes", "eps_arl_id")
    op.drop_column("incapacity_notes", "temporal_category_id")
    op.drop_table("diagnoses")
    op.drop_table("eps_arl_entities")
    op.drop_table("temporal_categories")

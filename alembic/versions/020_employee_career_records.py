"""Formación académica, capacitaciones y experiencia previa (fase 3)

Revision ID: 020
Revises: 019
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not _table_exists(table):
        return False
    return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def upgrade() -> None:
    if not _table_exists("employee_education"):
        op.create_table(
            "employee_education",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("education_level", sa.String(length=64), nullable=True),
            sa.Column("institution", sa.String(length=255), nullable=True),
            sa.Column("program", sa.String(length=255), nullable=True),
            sa.Column("graduation_year", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("certificate_url", sa.String(length=512), nullable=True),
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
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("employee_education", "ix_employee_education_employee_id"):
        op.create_index("ix_employee_education_employee_id", "employee_education", ["employee_id"])

    if not _table_exists("employee_training"):
        op.create_table(
            "employee_training",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("provider", sa.String(length=255), nullable=True),
            sa.Column("completed_at", sa.Date(), nullable=True),
            sa.Column("hours", sa.Integer(), nullable=True),
            sa.Column("training_type", sa.String(length=64), nullable=True),
            sa.Column("certificate_url", sa.String(length=512), nullable=True),
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
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("employee_training", "ix_employee_training_employee_id"):
        op.create_index("ix_employee_training_employee_id", "employee_training", ["employee_id"])

    if not _table_exists("employee_prior_jobs"):
        op.create_table(
            "employee_prior_jobs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("company_name", sa.String(length=255), nullable=False),
            sa.Column("position", sa.String(length=255), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("economic_sector", sa.String(length=128), nullable=True),
            sa.Column("leave_reason", sa.String(length=255), nullable=True),
            sa.Column("reference_phone", sa.String(length=64), nullable=True),
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
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("employee_prior_jobs", "ix_employee_prior_jobs_employee_id"):
        op.create_index("ix_employee_prior_jobs_employee_id", "employee_prior_jobs", ["employee_id"])


def downgrade() -> None:
    if _index_exists("employee_prior_jobs", "ix_employee_prior_jobs_employee_id"):
        op.drop_index("ix_employee_prior_jobs_employee_id", table_name="employee_prior_jobs")
    if _table_exists("employee_prior_jobs"):
        op.drop_table("employee_prior_jobs")
    if _index_exists("employee_training", "ix_employee_training_employee_id"):
        op.drop_index("ix_employee_training_employee_id", table_name="employee_training")
    if _table_exists("employee_training"):
        op.drop_table("employee_training")
    if _index_exists("employee_education", "ix_employee_education_employee_id"):
        op.drop_index("ix_employee_education_employee_id", table_name="employee_education")
    if _table_exists("employee_education"):
        op.drop_table("employee_education")

"""Expediente HR: datos personales, laborales y personas a cargo (fase 1)

Revision ID: 018
Revises: 017
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "018"
down_revision: Union[str, None] = "017"
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
    if not _table_exists("employee_personal"):
        op.create_table(
            "employee_personal",
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("first_name", sa.String(length=128), nullable=True),
            sa.Column("second_name", sa.String(length=128), nullable=True),
            sa.Column("first_surname", sa.String(length=128), nullable=True),
            sa.Column("second_surname", sa.String(length=128), nullable=True),
            sa.Column("document_type", sa.String(length=8), nullable=True),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column("gender", sa.String(length=32), nullable=True),
            sa.Column("marital_status", sa.String(length=32), nullable=True),
            sa.Column("children_count", sa.Integer(), nullable=True),
            sa.Column("residence_city", sa.String(length=128), nullable=True),
            sa.Column("residence_address", sa.String(length=255), nullable=True),
            sa.Column("neighborhood", sa.String(length=128), nullable=True),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("personal_email", sa.String(length=255), nullable=True),
            sa.Column("corporate_email", sa.String(length=255), nullable=True),
            sa.Column("photo_url", sa.String(length=512), nullable=True),
            sa.Column("blood_type", sa.String(length=8), nullable=True),
            sa.Column("rh_factor", sa.String(length=8), nullable=True),
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
            sa.PrimaryKeyConstraint("employee_id"),
        )
    if not _table_exists("employee_dependents"):
        op.create_table(
            "employee_dependents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("parentesco", sa.String(length=64), nullable=True),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column("schooling", sa.String(length=128), nullable=True),
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
    if not _index_exists("employee_dependents", "ix_employee_dependents_employee_id"):
        op.create_index(
            "ix_employee_dependents_employee_id", "employee_dependents", ["employee_id"]
        )
    if not _table_exists("employee_labor"):
        op.create_table(
            "employee_labor",
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("linkage_type", sa.String(length=64), nullable=True),
            sa.Column("temp_agency_name", sa.String(length=255), nullable=True),
            sa.Column("work_site_city", sa.String(length=128), nullable=True),
            sa.Column("hierarchical_level", sa.String(length=64), nullable=True),
            sa.Column("hire_date", sa.Date(), nullable=True),
            sa.Column("contract_type", sa.String(length=64), nullable=True),
            sa.Column("contract_end_date", sa.Date(), nullable=True),
            sa.Column("base_salary", sa.Numeric(14, 2), nullable=True),
            sa.Column("work_schedule_type", sa.String(length=64), nullable=True),
            sa.Column("work_modality", sa.String(length=32), nullable=True),
            sa.Column("eps_affiliation_number", sa.String(length=64), nullable=True),
            sa.Column("eps_name", sa.String(length=255), nullable=True),
            sa.Column("pension_fund", sa.String(length=255), nullable=True),
            sa.Column("severance_fund", sa.String(length=255), nullable=True),
            sa.Column("family_compensation_box", sa.String(length=255), nullable=True),
            sa.Column("arl_name", sa.String(length=255), nullable=True),
            sa.Column("arl_risk_level", sa.String(length=32), nullable=True),
            sa.Column("bank_name", sa.String(length=128), nullable=True),
            sa.Column("bank_account_type", sa.String(length=32), nullable=True),
            sa.Column("bank_account_number", sa.String(length=64), nullable=True),
            sa.Column("collaborator_status", sa.String(length=32), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
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
            sa.PrimaryKeyConstraint("employee_id"),
        )


def downgrade() -> None:
    if _table_exists("employee_labor"):
        op.drop_table("employee_labor")
    if _index_exists("employee_dependents", "ix_employee_dependents_employee_id"):
        op.drop_index("ix_employee_dependents_employee_id", table_name="employee_dependents")
    if _table_exists("employee_dependents"):
        op.drop_table("employee_dependents")
    if _table_exists("employee_personal"):
        op.drop_table("employee_personal")

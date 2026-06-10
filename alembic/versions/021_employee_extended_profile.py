"""Competencias, SST e historial interno (fase 4)

Revision ID: 021
Revises: 020
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS_COLS = [
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


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not _table_exists(table):
        return False
    return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def _create_simple_list_table(
    table: str,
    extra_columns: list[sa.Column],
) -> None:
    if _table_exists(table):
        return
    op.create_table(
        table,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        *extra_columns,
        *_TS_COLS,
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    idx = f"ix_{table}_employee_id"
    if not _index_exists(table, idx):
        op.create_index(idx, table, ["employee_id"])


def upgrade() -> None:
    _create_simple_list_table(
        "employee_languages",
        [
            sa.Column("language", sa.String(length=64), nullable=False),
            sa.Column("level", sa.String(length=32), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_software_skills",
        [
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("proficiency", sa.String(length=32), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_driving_licenses",
        [
            sa.Column("category", sa.String(length=16), nullable=False),
            sa.Column("expires_at", sa.Date(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_work_sst_certs",
        [
            sa.Column("cert_type", sa.String(length=64), nullable=False),
            sa.Column("issued_at", sa.Date(), nullable=True),
            sa.Column("expires_at", sa.Date(), nullable=True),
            sa.Column("certificate_url", sa.String(length=512), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_competency_evaluations",
        [
            sa.Column("period_label", sa.String(length=64), nullable=False),
            sa.Column("rating", sa.String(length=64), nullable=True),
            sa.Column("evaluator_name", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        ],
    )

    if not _table_exists("employee_sst_profiles"):
        op.create_table(
            "employee_sst_profiles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("entry_exam_date", sa.Date(), nullable=True),
            sa.Column("entry_medical_concept", sa.String(length=255), nullable=True),
            sa.Column("entry_restrictions", sa.Text(), nullable=True),
            sa.Column("occupational_disease", sa.Text(), nullable=True),
            sa.Column("current_medical_restrictions", sa.Text(), nullable=True),
            *_TS_COLS,
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("employee_id", name="uq_employee_sst_profiles_employee_id"),
        )
    if not _index_exists("employee_sst_profiles", "ix_employee_sst_profiles_employee_id"):
        op.create_index("ix_employee_sst_profiles_employee_id", "employee_sst_profiles", ["employee_id"])

    _create_simple_list_table(
        "employee_sst_periodic_exams",
        [
            sa.Column("exam_date", sa.Date(), nullable=True),
            sa.Column("result", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_sst_incapacities",
        [
            sa.Column("origin", sa.String(length=64), nullable=True),
            sa.Column("diagnosis", sa.String(length=255), nullable=True),
            sa.Column("days", sa.Integer(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_sst_accidents",
        [
            sa.Column("occurred_at", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("lost_days", sa.Integer(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_sst_ppe",
        [
            sa.Column("item_name", sa.String(length=255), nullable=False),
            sa.Column("delivered_at", sa.Date(), nullable=True),
            sa.Column("receipt_signed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        ],
    )
    _create_simple_list_table(
        "employee_contract_history",
        [
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("contract_type", sa.String(length=64), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_salary_history",
        [
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("previous_salary", sa.Numeric(14, 2), nullable=True),
            sa.Column("new_salary", sa.Numeric(14, 2), nullable=True),
            sa.Column("reason", sa.String(length=255), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_performance_reviews",
        [
            sa.Column("period_label", sa.String(length=64), nullable=False),
            sa.Column("rating", sa.String(length=64), nullable=True),
            sa.Column("evaluator_name", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_recognitions",
        [
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("recognized_at", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_disciplinary_actions",
        [
            sa.Column("action_type", sa.String(length=64), nullable=False),
            sa.Column("occurred_at", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
        ],
    )
    _create_simple_list_table(
        "employee_absence_records",
        [
            sa.Column("absence_type", sa.String(length=64), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("days", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        ],
    )


def downgrade() -> None:
    tables = [
        "employee_absence_records",
        "employee_disciplinary_actions",
        "employee_recognitions",
        "employee_performance_reviews",
        "employee_salary_history",
        "employee_contract_history",
        "employee_sst_ppe",
        "employee_sst_accidents",
        "employee_sst_incapacities",
        "employee_sst_periodic_exams",
        "employee_sst_profiles",
        "employee_competency_evaluations",
        "employee_work_sst_certs",
        "employee_driving_licenses",
        "employee_software_skills",
        "employee_languages",
    ]
    for table in tables:
        idx = f"ix_{table}_employee_id"
        if _index_exists(table, idx):
            op.drop_index(idx, table_name=table)
        if _table_exists(table):
            op.drop_table(table)

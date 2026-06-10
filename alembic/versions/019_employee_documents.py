"""Documentos del expediente HR

Revision ID: 019
Revises: 018
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "019"
down_revision: Union[str, None] = "018"
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
    if not _table_exists("employee_documents"):
        op.create_table(
            "employee_documents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("document_kind", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("file_url", sa.String(length=512), nullable=False),
            sa.Column("content_type", sa.String(length=128), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="vigente"),
            sa.Column("expires_at", sa.Date(), nullable=True),
            sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
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
            sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("employee_documents", "ix_employee_documents_employee_id"):
        op.create_index(
            "ix_employee_documents_employee_id", "employee_documents", ["employee_id"]
        )
    if not _index_exists("employee_documents", "ix_employee_documents_document_kind"):
        op.create_index(
            "ix_employee_documents_document_kind", "employee_documents", ["document_kind"]
        )
    if not _index_exists("employee_documents", "ix_employee_documents_status"):
        op.create_index("ix_employee_documents_status", "employee_documents", ["status"])


def downgrade() -> None:
    if _index_exists("employee_documents", "ix_employee_documents_status"):
        op.drop_index("ix_employee_documents_status", table_name="employee_documents")
    if _index_exists("employee_documents", "ix_employee_documents_document_kind"):
        op.drop_index("ix_employee_documents_document_kind", table_name="employee_documents")
    if _index_exists("employee_documents", "ix_employee_documents_employee_id"):
        op.drop_index("ix_employee_documents_employee_id", table_name="employee_documents")
    if _table_exists("employee_documents"):
        op.drop_table("employee_documents")

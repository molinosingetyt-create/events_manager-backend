"""Incapacidad: soporte y nota de prórroga opcionales; descripción opcional

Revision ID: 025
Revises: 024
Create Date: 2026-06-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "incapacity_extensions",
        "file_url",
        existing_type=sa.String(length=1024),
        nullable=True,
    )
    op.alter_column(
        "incapacity_extensions",
        "note",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "incapacity_notes",
        "description",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "incapacity_notes",
        "description",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "incapacity_extensions",
        "note",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "incapacity_extensions",
        "file_url",
        existing_type=sa.String(length=1024),
        nullable=False,
    )

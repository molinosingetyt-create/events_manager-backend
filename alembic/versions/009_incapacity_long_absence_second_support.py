"""incapacity_notes: soporte adicional HC y texto transcrito EPS

Revision ID: 009
Revises: 008
Create Date: 2026-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incapacity_notes",
        sa.Column("long_absence_second_file_url", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "incapacity_notes",
        sa.Column("long_absence_eps_transcribed_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("incapacity_notes", "long_absence_eps_transcribed_text")
    op.drop_column("incapacity_notes", "long_absence_second_file_url")

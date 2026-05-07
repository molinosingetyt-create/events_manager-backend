"""incapacity_notes: tipo enfermedad general / accidente trabajo

Revision ID: 011
Revises: 010
Create Date: 2026-04-01

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        text(
            """
            UPDATE incapacity_notes SET type = 'general_illness' WHERE type = 'incapacity'
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE incapacity_notes SET type = 'work_accident' WHERE type = 'note'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            UPDATE incapacity_notes SET type = 'incapacity' WHERE type = 'general_illness'
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE incapacity_notes SET type = 'note' WHERE type = 'work_accident'
            """
        )
    )

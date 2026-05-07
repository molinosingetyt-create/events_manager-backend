"""employees: categoría temporal

Revision ID: 010
Revises: 009
Create Date: 2026-04-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("temporal_category_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_employees_temporal_category_id",
        "employees",
        "temporal_categories",
        ["temporal_category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        text(
            """
            UPDATE employees e
            SET temporal_category_id = (
                SELECT id FROM temporal_categories
                WHERE status = 'active'
                ORDER BY id ASC
                LIMIT 1
            )
            WHERE e.temporal_category_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_employees_temporal_category_id", "employees", type_="foreignkey")
    op.drop_column("employees", "temporal_category_id")

"""Rellenar permissions/profiles si la BD se creó con create_all antes de Alembic.

Revision ID: 013
Revises: 012
Create Date: 2026-05-07

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from app.db.rbac_seed import seed_rbac_sync

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    n = conn.execute(text("SELECT COUNT(*) FROM permissions")).scalar()
    if n and n > 0:
        return
    seed_rbac_sync(conn)


def downgrade() -> None:
    pass

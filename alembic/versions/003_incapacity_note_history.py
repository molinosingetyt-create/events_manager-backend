"""incapacity note history timeline

Revision ID: 003
Revises: 002
Create Date: 2025-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "incapacity_note_history" not in insp.get_table_names():
        op.create_table(
            "incapacity_note_history",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("incapacity_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("snapshot", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["incapacity_id"], ["incapacity_notes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    insp = inspect(bind)
    ix_name = op.f("ix_incapacity_note_history_incapacity_id")
    existing = {i["name"] for i in insp.get_indexes("incapacity_note_history")}
    if ix_name not in existing:
        op.create_index(
            ix_name,
            "incapacity_note_history",
            ["incapacity_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "incapacity_note_history" not in insp.get_table_names():
        return
    ix_name = op.f("ix_incapacity_note_history_incapacity_id")
    existing = {i["name"] for i in insp.get_indexes("incapacity_note_history")}
    if ix_name in existing:
        op.drop_index(ix_name, table_name="incapacity_note_history")
    op.drop_table("incapacity_note_history")

"""app notifications for overtime

Revision ID: 004
Revises: 003
Create Date: 2025-03-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "app_notifications" in insp.get_table_names():
        return
    op.create_table(
        "app_notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("overtime_request_id", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["overtime_request_id"], ["overtime_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "overtime_request_id", "kind", name="uq_app_notif_user_ot_kind"),
    )
    op.create_index(op.f("ix_app_notifications_user_id"), "app_notifications", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_app_notifications_overtime_request_id"),
        "app_notifications",
        ["overtime_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_app_notifications_overtime_request_id"), table_name="app_notifications")
    op.drop_index(op.f("ix_app_notifications_user_id"), table_name="app_notifications")
    op.drop_table("app_notifications")

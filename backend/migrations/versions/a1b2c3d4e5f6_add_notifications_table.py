"""add notifications table

Revision ID: a1b2c3d4e5f6
Revises: 7f4c2a9d1b1e
Create Date: 2026-04-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "7f4c2a9d1b1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recipient_user_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("image_id", sa.UUID(), nullable=False),
        sa.Column("notification_type", sa.String(20), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
    op.create_index("ix_notifications_actor_user_id", "notifications", ["actor_user_id"])
    op.create_index("ix_notifications_image_id", "notifications", ["image_id"])
    op.create_index(
        "ix_notifications_recipient_created_at",
        "notifications",
        ["recipient_user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_created_at", table_name="notifications")
    op.drop_index("ix_notifications_image_id", table_name="notifications")
    op.drop_index("ix_notifications_actor_user_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_table("notifications")

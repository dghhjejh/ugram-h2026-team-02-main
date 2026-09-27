"""add async search trends pipeline

Revision ID: 7f4c2a9d1b1e
Revises: 2e002e23bc83
Create Date: 2026-03-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f4c2a9d1b1e"
down_revision: str | Sequence[str] | None = "2e002e23bc83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_table("search_events"):
        op.create_table(
            "search_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("keyword", sa.String(length=100), nullable=False),
            sa.Column("trend_type", sa.String(length=20), nullable=False),
            sa.Column("search_date", sa.Date(), nullable=False),
            sa.Column("searched_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_search_events_processed_at", "search_events", ["processed_at"], unique=False)
        op.create_index(
            "ix_search_events_search_date_type", "search_events", ["search_date", "trend_type"], unique=False
        )

    if not _has_table("search_trends_daily"):
        op.create_table(
            "search_trends_daily",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("keyword", sa.String(length=100), nullable=False),
            sa.Column("trend_type", sa.String(length=20), nullable=False),
            sa.Column("search_date", sa.Date(), nullable=False),
            sa.Column("search_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "keyword", "trend_type", "search_date", name="uq_search_trends_daily_keyword_type_date"
            ),
        )
        op.create_index(
            "ix_search_trends_daily_date_type_count",
            "search_trends_daily",
            ["search_date", "trend_type", "search_count"],
            unique=False,
        )

    if _has_table("search_trends"):
        bind = op.get_bind()
        bind.execute(
            sa.text(
                """
                INSERT INTO search_trends_daily (id, keyword, trend_type, search_date, search_count, created_at, updated_at)
                SELECT id, keyword, trend_type, search_date, search_count, created_at, updated_at
                FROM search_trends
                """
            )
        )
        op.drop_table("search_trends")


def downgrade() -> None:
    """Downgrade schema."""
    if _has_table("search_trends_daily"):
        op.drop_index("ix_search_trends_daily_date_type_count", table_name="search_trends_daily")
        op.drop_table("search_trends_daily")

    if _has_table("search_events"):
        op.drop_index("ix_search_events_search_date_type", table_name="search_events")
        op.drop_index("ix_search_events_processed_at", table_name="search_events")
        op.drop_table("search_events")

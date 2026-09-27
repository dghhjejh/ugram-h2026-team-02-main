"""'On cascade property added for user deletion'

Revision ID: 2e002e23bc83
Revises:
Create Date: 2026-03-12 15:51:27.541507

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2e002e23bc83"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_images_owner_fk_names() -> list[str]:
    """Return FK constraint names for images.owner_user_id -> users.id."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("images") or not inspector.has_table("users"):
        return []

    fk_names: list[str] = []
    for fk in inspector.get_foreign_keys("images"):
        constrained_columns = fk.get("constrained_columns") or []
        referred_table = fk.get("referred_table")
        referred_columns = fk.get("referred_columns") or []
        fk_name = fk.get("name")

        if (
            constrained_columns == ["owner_user_id"]
            and referred_table == "users"
            and referred_columns == ["id"]
            and fk_name
        ):
            fk_names.append(fk_name)

    return fk_names


def _has_required_tables() -> bool:
    """Check whether required tables exist before altering constraints."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table("images") and inspector.has_table("users")


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_required_tables():
        return

    for fk_name in _get_images_owner_fk_names():
        op.drop_constraint(fk_name, "images", type_="foreignkey")

    op.create_foreign_key(
        "fk_images_owner_user_id_users",
        source_table="images",
        referent_table="users",
        local_cols=["owner_user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    if not _has_required_tables():
        return

    for fk_name in _get_images_owner_fk_names():
        op.drop_constraint(fk_name, "images", type_="foreignkey")

    op.create_foreign_key(
        "fk_images_owner_user_id_users",
        source_table="images",
        referent_table="users",
        local_cols=["owner_user_id"],
        remote_cols=["id"],
    )

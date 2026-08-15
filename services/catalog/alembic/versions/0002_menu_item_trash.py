"""add menu_items.deleted_at (trash / soft-delete)

Adds `menu_items.deleted_at` — a nullable timestamp marking when an item was moved to
trash. NULL means "not trashed". Deliberately separate from the existing `active`/
`in_stock` columns, which control order-grid visibility for the existing "toggle
availability" feature and are a different concept (confirmed by direct inspection of
every caller before this migration was written — conflating them would have broken that
feature). Every default listing query (list_items/list_all_items/bulk_price_update in
`MenuService`) excludes rows where this is non-null; a real `DELETE` only ever happens via
`MenuService.permanently_delete_item`, and only on an already-trashed item.

Revision ID: 0002_menu_item_trash
Revises: 0001_baseline
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_menu_item_trash"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_items", "deleted_at")

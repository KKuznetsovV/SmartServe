"""add reports attribution/category-snapshot columns

Adds `orders.created_by` (who created the order — server attribution for the new "sales per
server" report) and `order_items.category_id`/`category_name` (a point-in-time category
snapshot captured when the item is added, for the new "sales by category" report — mirrors
the existing `menu_item_name` snapshot pattern already used on this table).

`services/reporting` maps its own trimmed `Order`/`OrderItem` models onto these same
physical tables and gets matching Python-side columns added in that service's models.py —
no DDL is needed on reporting's side since this is the one physical ALTER TABLE.

Revision ID: 0002_reports_columns
Revises: 0001_baseline
Create Date: 2026-08-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_reports_columns"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # created_by references auth's `users` table (cross-service) — plain column, not an
    # enforced FK, consistent with `comped_by` on order_items.
    op.add_column("orders", sa.Column("created_by", sa.String(), nullable=True))
    op.add_column("order_items", sa.Column("category_id", sa.String(), nullable=True))
    op.add_column("order_items", sa.Column("category_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("order_items", "category_name")
    op.drop_column("order_items", "category_id")
    op.drop_column("orders", "created_by")

"""snapshot Hebrew names on order lines

Revision ID: 0010_order_item_name_he
Revises: 0009_daily_order_numbers
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_order_item_name_he"
down_revision: str | None = "0009_daily_order_numbers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("menu_item_name_he", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("order_items", "menu_item_name_he")

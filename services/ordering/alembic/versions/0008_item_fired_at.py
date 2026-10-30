"""guard order.item_fired with order_items.fired_at

Revision ID: 0008_item_fired_at
Revises: 0007_order_vat_rate
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_item_fired_at"
down_revision: str | None = "0007_order_vat_rate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("order_items", "fired_at")

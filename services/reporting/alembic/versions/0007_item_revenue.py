"""store net line revenue on reporting_order_items

Revision ID: 0007_item_revenue
Revises: 0006_order_tax_amount
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_item_revenue"
down_revision: str | None = "0006_order_tax_amount"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reporting_order_items",
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "reporting_order_items",
        sa.Column("is_comped", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "reporting_order_items",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.add_column(
        "reporting_order_items",
        sa.Column("revenue", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.execute("UPDATE reporting_order_items SET revenue = qty * unit_price")


def downgrade() -> None:
    op.drop_column("reporting_order_items", "revenue")
    op.drop_column("reporting_order_items", "status")
    op.drop_column("reporting_order_items", "is_comped")
    op.drop_column("reporting_order_items", "discount_amount")

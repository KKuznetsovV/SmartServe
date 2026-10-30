"""create reporting_orders and reporting_order_items and backfill from ordering

Revision ID: 0003_reporting_order_projection
Revises: 0002_event_log_business_id
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_reporting_order_projection"
down_revision: str | None = "0002_event_log_business_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reporting_orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False, server_default="dine_in"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reporting_orders_location_id", "reporting_orders", ["location_id"])
    op.create_table(
        "reporting_order_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), sa.ForeignKey("reporting_orders.id"), nullable=False),
        sa.Column("menu_item_id", sa.String(), nullable=True),
        sa.Column("menu_item_name", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.String(), nullable=True),
        sa.Column("category_name", sa.String(length=255), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
    )
    op.create_index("ix_reporting_order_items_order_id", "reporting_order_items", ["order_id"])
    op.execute(
        """
        INSERT INTO reporting_orders (
            id, location_id, channel, status, total, created_by, created_at, version, occurred_at
        )
        SELECT
            id,
            location_id,
            channel,
            status,
            total,
            created_by,
            created_at,
            0,
            COALESCE(updated_at, created_at)
        FROM orders
        """
    )
    op.execute(
        """
        INSERT INTO reporting_order_items (
            id, order_id, menu_item_id, menu_item_name, category_id, category_name, qty, unit_price
        )
        SELECT
            id,
            order_id,
            menu_item_id,
            menu_item_name,
            category_id,
            category_name,
            qty,
            unit_price
        FROM order_items
        """
    )


def downgrade() -> None:
    op.drop_index("ix_reporting_order_items_order_id", table_name="reporting_order_items")
    op.drop_table("reporting_order_items")
    op.drop_index("ix_reporting_orders_location_id", table_name="reporting_orders")
    op.drop_table("reporting_orders")

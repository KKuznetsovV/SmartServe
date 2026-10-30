"""daily order numbers per location and business date

Revision ID: 0009_daily_order_numbers
Revises: 0008_item_fired_at
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_daily_order_numbers"
down_revision: str | None = "0008_item_fired_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("order_number", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("business_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE orders
        SET
            business_date = (created_at AT TIME ZONE 'UTC')::date,
            order_number = numbered.n
        FROM (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY location_id, (created_at AT TIME ZONE 'UTC')::date
                    ORDER BY created_at, id
                ) AS n
            FROM orders
        ) AS numbered
        WHERE orders.id = numbered.id
        """
    )
    op.alter_column("orders", "order_number", nullable=False)
    op.alter_column("orders", "business_date", nullable=False)
    op.create_unique_constraint(
        "uq_orders_location_business_date_number",
        "orders",
        ["location_id", "business_date", "order_number"],
    )
    op.create_table(
        "order_number_counters",
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("location_id", "business_date"),
    )
    op.execute(
        """
        INSERT INTO order_number_counters (location_id, business_date, last_number)
        SELECT location_id, business_date, MAX(order_number)
        FROM orders
        GROUP BY location_id, business_date
        """
    )


def downgrade() -> None:
    op.drop_table("order_number_counters")
    op.drop_constraint("uq_orders_location_business_date_number", "orders", type_="unique")
    op.drop_column("orders", "business_date")
    op.drop_column("orders", "order_number")

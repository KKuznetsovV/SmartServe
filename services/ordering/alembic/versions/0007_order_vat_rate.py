"""snapshot VAT rate on orders

Menu prices are VAT-inclusive shelf prices. Existing catalog prices are not converted.
Existing orders keep their stored totals; vat_rate is backfilled so later recomputes
extract inclusive VAT at the rate that applied when the order was created.

Revision ID: 0007_order_vat_rate
Revises: 0006_numeric_money
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_order_vat_rate"
down_revision: str | None = "0006_numeric_money"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("vat_rate", sa.Numeric(5, 4), nullable=False, server_default="0.18"),
    )
    op.execute(
        """
        UPDATE orders
        SET vat_rate = CASE
            WHEN created_at < TIMESTAMPTZ '2025-01-01 00:00:00+00' THEN 0.17
            ELSE 0.18
        END
        """
    )


def downgrade() -> None:
    op.drop_column("orders", "vat_rate")

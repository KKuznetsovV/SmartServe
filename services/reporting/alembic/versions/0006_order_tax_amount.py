"""project tax_amount onto reporting_orders for VAT collected

Revision ID: 0006_order_tax_amount
Revises: 0005_numeric_money
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_order_tax_amount"
down_revision: str | None = "0005_numeric_money"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reporting_orders",
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE reporting_orders AS r
        SET tax_amount = o.tax_amount
        FROM orders AS o
        WHERE o.id = r.id
        """
    )


def downgrade() -> None:
    op.drop_column("reporting_orders", "tax_amount")

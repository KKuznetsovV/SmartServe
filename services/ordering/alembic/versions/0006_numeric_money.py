"""ordering money columns to numeric

Revision ID: 0006_numeric_money
Revises: 0005_outbox
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from smartserve_shared.money import alter_to_float, alter_to_numeric

revision: str = "0006_numeric_money"
down_revision: str | None = "0005_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("subtotal", "tax_amount", "discount_amount", "total"):
        alter_to_numeric("orders", column, 10, 2)
    for column in ("unit_price", "discount_value", "discount_amount"):
        alter_to_numeric("order_items", column, 10, 2)


def downgrade() -> None:
    for column in ("subtotal", "tax_amount", "discount_amount", "total"):
        alter_to_float("orders", column)
    for column in ("unit_price", "discount_value", "discount_amount"):
        alter_to_float("order_items", column)

"""catalog money columns to numeric

Revision ID: 0005_numeric_money
Revises: 0004_outbox
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from smartserve_shared.money import alter_to_float, alter_to_numeric

revision: str = "0005_numeric_money"
down_revision: str | None = "0004_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    alter_to_numeric("menu_items", "price", 10, 2)
    alter_to_numeric("menu_items", "tax_rate", 5, 4)
    alter_to_numeric("modifiers", "price_delta", 10, 2)
    alter_to_numeric("discounts", "value", 10, 2)
    alter_to_numeric("discounts", "min_order_amount", 10, 2)


def downgrade() -> None:
    alter_to_float("menu_items", "price")
    alter_to_float("menu_items", "tax_rate")
    alter_to_float("modifiers", "price_delta")
    alter_to_float("discounts", "value")
    alter_to_float("discounts", "min_order_amount")

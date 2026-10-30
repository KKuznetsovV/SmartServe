"""reporting projection money columns to numeric

Revision ID: 0005_numeric_money
Revises: 0004_processed_events
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from smartserve_shared.money import alter_to_float, alter_to_numeric

revision: str = "0005_numeric_money"
down_revision: str | None = "0004_processed_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    alter_to_numeric("reporting_orders", "total", 10, 2)
    alter_to_numeric("reporting_order_items", "unit_price", 10, 2)


def downgrade() -> None:
    alter_to_float("reporting_orders", "total")
    alter_to_float("reporting_order_items", "unit_price")

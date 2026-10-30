"""payments money columns to numeric

Revision ID: 0004_numeric_money
Revises: 0003_outbox
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from smartserve_shared.money import alter_to_float, alter_to_numeric

revision: str = "0004_numeric_money"
down_revision: str | None = "0003_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    alter_to_numeric("payments", "amount", 10, 2)
    alter_to_numeric("payments", "tip_amount", 10, 2)


def downgrade() -> None:
    alter_to_float("payments", "amount")
    alter_to_float("payments", "tip_amount")

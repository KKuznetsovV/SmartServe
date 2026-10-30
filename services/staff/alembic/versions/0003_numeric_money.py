"""staff shift cash columns to numeric

Revision ID: 0003_numeric_money
Revises: 0002_drop_users_fks
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from smartserve_shared.money import alter_to_float, alter_to_numeric

revision: str = "0003_numeric_money"
down_revision: str | None = "0002_drop_users_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    alter_to_numeric("shifts", "opening_cash", 10, 2)
    alter_to_numeric("shifts", "closing_cash", 10, 2)


def downgrade() -> None:
    alter_to_float("shifts", "opening_cash")
    alter_to_float("shifts", "closing_cash")

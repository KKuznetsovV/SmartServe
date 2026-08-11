"""add tip_amount and guest_number to payments, supporting split/per-guest payments

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
Create Date: 2026-08-06 16:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("tip_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("guest_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "guest_number")
    op.drop_column("payments", "tip_amount")

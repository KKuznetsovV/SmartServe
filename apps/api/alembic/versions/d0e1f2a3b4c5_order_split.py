"""add guest_number and split_from_order_id to orders, enabling per-guest order splitting

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-06 12:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("guest_number", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("split_from_order_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_orders_split_from_order_id", "orders", "orders", ["split_from_order_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_orders_split_from_order_id", "orders", type_="foreignkey")
    op.drop_column("orders", "split_from_order_id")
    op.drop_column("orders", "guest_number")

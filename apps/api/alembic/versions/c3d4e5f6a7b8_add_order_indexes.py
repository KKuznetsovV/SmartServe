"""add order indexes for hot-path queries

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-01 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ix_orders_location_status and ix_order_items_order_id already exist from the initial schema
    op.create_index("ix_orders_location_created", "orders", ["location_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_orders_location_created", table_name="orders")

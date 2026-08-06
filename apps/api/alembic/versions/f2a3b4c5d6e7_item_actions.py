"""replace order-level split (guest_number/split_from_order_id on orders) with
in-place per-item guest tagging, plus per-item discount and on-the-house comp fields

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-06 15:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_orders_split_from_order_id", "orders", type_="foreignkey")
    op.drop_column("orders", "split_from_order_id")
    op.drop_column("orders", "guest_number")

    op.add_column("order_items", sa.Column("guest_number", sa.Integer(), nullable=True))
    op.add_column("order_items", sa.Column("discount_type", sa.String(length=20), nullable=True))
    op.add_column("order_items", sa.Column("discount_value", sa.Float(), nullable=True))
    op.add_column(
        "order_items", sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0")
    )
    op.add_column(
        "order_items", sa.Column("is_comped", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("order_items", sa.Column("comped_by", sa.String(), nullable=True))
    op.create_foreign_key("fk_order_items_comped_by", "order_items", "users", ["comped_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_order_items_comped_by", "order_items", type_="foreignkey")
    op.drop_column("order_items", "comped_by")
    op.drop_column("order_items", "is_comped")
    op.drop_column("order_items", "discount_amount")
    op.drop_column("order_items", "discount_value")
    op.drop_column("order_items", "discount_type")
    op.drop_column("order_items", "guest_number")

    op.add_column("orders", sa.Column("guest_number", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("split_from_order_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_orders_split_from_order_id", "orders", "orders", ["split_from_order_id"], ["id"]
    )

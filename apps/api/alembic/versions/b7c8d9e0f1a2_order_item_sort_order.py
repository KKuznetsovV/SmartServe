"""add sort_order to order_items, enabling drag-and-drop reordering within an order

Revision ID: b7c8d9e0f1a2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-06 08:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_items", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("order_items", "sort_order")

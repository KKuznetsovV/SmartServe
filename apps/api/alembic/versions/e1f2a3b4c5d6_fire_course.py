"""add fire-course fields: MenuItem.default_fire_course, OrderItem.fire_course, Order.fired_courses

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-06 13:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "menu_items", sa.Column("default_fire_course", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("order_items", sa.Column("fire_course", sa.Integer(), nullable=False, server_default="1"))
    op.add_column(
        "orders", sa.Column("fired_courses", sa.JSON(), nullable=False, server_default="[]")
    )


def downgrade() -> None:
    op.drop_column("orders", "fired_courses")
    op.drop_column("order_items", "fire_course")
    op.drop_column("menu_items", "default_fire_course")

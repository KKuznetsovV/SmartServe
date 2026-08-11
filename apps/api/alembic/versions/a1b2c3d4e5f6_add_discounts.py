"""add discounts table and order discount columns

Revision ID: a1b2c3d4e5f6
Revises: 8e5b71307816
Create Date: 2026-07-31 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "8e5b71307816"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="percent"),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("min_order_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "code", name="uq_discounts_business_code"),
    )
    op.create_index("ix_discounts_business_id", "discounts", ["business_id"])

    op.add_column("orders", sa.Column("discount_id", sa.String(), sa.ForeignKey("discounts.id"), nullable=True))
    op.add_column("orders", sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "discount_id")
    op.drop_index("ix_discounts_business_id", table_name="discounts")
    op.drop_table("discounts")

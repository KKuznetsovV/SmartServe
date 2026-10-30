"""tendered, change, idempotency key and refund linkage on payments

Revision ID: 0005_payment_rules
Revises: 0004_numeric_money
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_payment_rules"
down_revision: str | None = "0004_numeric_money"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("tendered", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "payments",
        sa.Column("change_due", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column("payments", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("refund_of_id", sa.String(), nullable=True))
    op.create_index(
        "uq_payments_order_idempotency",
        "payments",
        ["order_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        sqlite_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_order_idempotency", table_name="payments")
    op.drop_column("payments", "refund_of_id")
    op.drop_column("payments", "idempotency_key")
    op.drop_column("payments", "change_due")
    op.drop_column("payments", "tendered")

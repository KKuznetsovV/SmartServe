"""baseline: create printing-owned tables (printers, printer_routes, print_jobs)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "printers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, server_default="receipt"),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("port", sa.Integer(), nullable=False, server_default="9100"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "printer_routes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("printer_id", sa.String(), sa.ForeignKey("printers.id"), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.UniqueConstraint("printer_id", "item_id"),
    )
    op.create_table(
        "print_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("printer_id", sa.String(), sa.ForeignKey("printers.id"), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("print_jobs")
    op.drop_table("printer_routes")
    op.drop_table("printers")

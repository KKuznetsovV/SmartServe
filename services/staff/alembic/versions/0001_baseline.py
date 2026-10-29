"""baseline: create staff-owned table (shifts)

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
        "shifts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("opened_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("closed_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_cash", sa.Float(), nullable=False, server_default="0"),
        sa.Column("closing_cash", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("shifts")

"""add shifts table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-31 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shifts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("opened_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("closed_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_cash", sa.Float(), nullable=False, server_default="0"),
        sa.Column("closing_cash", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shifts_location_id", "shifts", ["location_id"])
    op.create_index("ix_shifts_status", "shifts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_shifts_status", table_name="shifts")
    op.drop_index("ix_shifts_location_id", table_name="shifts")
    op.drop_table("shifts")

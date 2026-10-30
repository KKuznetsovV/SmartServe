"""add monotonically increasing orders.version for event projection

Revision ID: 0003_order_event_version
Revises: 0002_reports_columns
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_order_event_version"
down_revision: str | None = "0002_reports_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("orders", "version", server_default=None)


def downgrade() -> None:
    op.drop_column("orders", "version")

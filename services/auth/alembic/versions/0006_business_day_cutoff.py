"""location business-day cutoff for reports and order numbers

Revision ID: 0006_business_day_cutoff
Revises: 0005_devices
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_business_day_cutoff"
down_revision: str | None = "0005_devices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column("business_day_cutoff", sa.Time(), nullable=False, server_default="05:00:00"),
    )


def downgrade() -> None:
    op.drop_column("locations", "business_day_cutoff")

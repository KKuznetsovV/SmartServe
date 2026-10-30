"""create printing_processed_events

Revision ID: 0002_processed_events
Revises: 0001_baseline
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from alembic import op
from smartserve_shared.outbox import create_processed_events_table, drop_processed_events_table

revision: str = "0002_processed_events"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_processed_events_table(op, "printing_processed_events")


def downgrade() -> None:
    drop_processed_events_table(op, "printing_processed_events")

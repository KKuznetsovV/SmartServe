"""create ordering_outbox and ordering_processed_events

Revision ID: 0005_outbox
Revises: 0004_drop_cross_service_fks
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from alembic import op
from smartserve_shared.outbox import (
    create_outbox_table,
    create_processed_events_table,
    drop_outbox_table,
    drop_processed_events_table,
)

revision: str = "0005_outbox"
down_revision: str | None = "0004_drop_cross_service_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_outbox_table(op, "ordering_outbox")
    create_processed_events_table(op, "ordering_processed_events")


def downgrade() -> None:
    drop_processed_events_table(op, "ordering_processed_events")
    drop_outbox_table(op, "ordering_outbox")

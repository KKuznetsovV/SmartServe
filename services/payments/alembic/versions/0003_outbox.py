"""create payments_outbox

Revision ID: 0003_outbox
Revises: 0002_drop_orders_fk
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from alembic import op
from smartserve_shared.outbox import create_outbox_table, drop_outbox_table

revision: str = "0003_outbox"
down_revision: str | None = "0002_drop_orders_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_outbox_table(op, "payments_outbox")


def downgrade() -> None:
    drop_outbox_table(op, "payments_outbox")

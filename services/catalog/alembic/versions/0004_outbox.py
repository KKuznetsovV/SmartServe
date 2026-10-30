"""create catalog_outbox

Revision ID: 0004_outbox
Revises: 0003_modifier_delete_cascade
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from alembic import op
from smartserve_shared.outbox import create_outbox_table, drop_outbox_table

revision: str = "0004_outbox"
down_revision: str | None = "0003_modifier_delete_cascade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_outbox_table(op, "catalog_outbox")


def downgrade() -> None:
    drop_outbox_table(op, "catalog_outbox")

"""create auth_outbox

Revision ID: 0003_outbox
Revises: 0002_lowercase_email_unique
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from alembic import op
from smartserve_shared.outbox import create_outbox_table, drop_outbox_table

revision: str = "0003_outbox"
down_revision: str | None = "0002_lowercase_email_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_outbox_table(op, "auth_outbox")


def downgrade() -> None:
    drop_outbox_table(op, "auth_outbox")

"""baseline: create event_log (the one table reporting owns)

This is a greenfield baseline for the reporting service's first-ever Alembic chain — no
Alembic previously existed for services/* (see docs/microservices-plan.md / repo notes).
`users`/`locations`/`orders`/`order_items` are trimmed, read-only mirrors of tables owned
and migrated by `auth`/`ordering` respectively and are intentionally NOT created here.

NOTE for environments where `event_log` already exists (e.g. a long-running dev database
whose schema predates this migration): run `alembic stamp 0001_baseline` instead of
`alembic upgrade head` to mark this revision as already applied without re-running the DDL.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("event_log")

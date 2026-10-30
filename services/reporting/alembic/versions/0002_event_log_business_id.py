"""add indexed event_log.business_id and backfill from payload / locations

Revision ID: 0002_event_log_business_id
Revises: 0001_baseline
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_event_log_business_id"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("event_log", sa.Column("business_id", sa.String(), nullable=True))
    op.create_index("ix_event_log_business_id", "event_log", ["business_id"])
    op.execute(
        """
        UPDATE event_log
        SET business_id = payload::json->>'businessId'
        WHERE business_id IS NULL
          AND payload::json->>'businessId' IS NOT NULL
          AND payload::json->>'businessId' <> ''
        """
    )
    op.execute(
        """
        UPDATE event_log AS e
        SET business_id = l.business_id
        FROM locations AS l
        WHERE e.business_id IS NULL
          AND payload::json->>'locationId' IS NOT NULL
          AND payload::json->>'locationId' = l.id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_event_log_business_id", table_name="event_log")
    op.drop_column("event_log", "business_id")

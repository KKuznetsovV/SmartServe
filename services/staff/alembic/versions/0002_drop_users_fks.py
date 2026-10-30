"""drop shifts FKs onto auth-owned users

Revision ID: 0002_drop_users_fks
Revises: 0001_baseline
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_drop_users_fks"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class rel ON rel.oid = c.conrelid
            JOIN pg_attribute a ON a.attrelid = rel.oid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f'
              AND rel.relname = 'shifts'
              AND a.attname IN ('opened_by', 'closed_by')
          LOOP
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', 'shifts', r.conname);
          END LOOP;
        END $$;
        """)
    )


def downgrade() -> None:
    pass

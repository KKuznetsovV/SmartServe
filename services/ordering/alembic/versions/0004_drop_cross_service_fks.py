"""drop leftover cross-service FKs on ordering-owned tables

Revision ID: 0004_drop_cross_service_fks
Revises: 0003_order_event_version
Create Date: 2026-10-30

Ordering's baseline never created these constraints; they exist on databases that
inherited the old monolith schema. Drop them so catalog can permanently delete a
menu item that still appears on historical order lines.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_drop_cross_service_fks"
down_revision: str | None = "0003_order_event_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TARGETS: tuple[tuple[str, str], ...] = (
    ("tables", "location_id"),
    ("orders", "location_id"),
    ("orders", "created_by"),
    ("orders", "discount_id"),
    ("order_items", "menu_item_id"),
    ("order_items", "comped_by"),
)


def _drop_fks(table: str, column: str) -> None:
    op.execute(
        sa.text(f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class rel ON rel.oid = c.conrelid
            JOIN pg_attribute a ON a.attrelid = rel.oid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f'
              AND rel.relname = '{table}'
              AND a.attname = '{column}'
          LOOP
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', '{table}', r.conname);
          END LOOP;
        END $$;
        """)
    )


def upgrade() -> None:
    for table, column in _TARGETS:
        _drop_fks(table, column)


def downgrade() -> None:
    pass

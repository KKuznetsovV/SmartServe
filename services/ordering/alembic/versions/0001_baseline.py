"""baseline: create ordering-owned tables (tables, orders, order_items)

This is a greenfield baseline for the ordering service's first-ever Alembic chain — no
Alembic previously existed for services/* (see docs/microservices-plan.md / repo notes).
It reflects the schema these tables have had since services/ordering was extracted, i.e.
the state BEFORE the `created_by`/`category_id`/`category_name` columns added in the next
revision. Only tables ordering owns are created here; `businesses`/`locations`/`users`/
`menu_items`/`menu_categories`/`discounts` are trimmed mirrors owned by `auth`/`catalog` and
are intentionally NOT created by this migration.

NOTE for environments where these tables already exist (e.g. a long-running dev database
whose schema predates this migration, inherited from the retired `apps/api` monolith): run
`alembic stamp 0001_baseline` instead of `alembic upgrade head` to mark this revision as
already applied without re-running the DDL, then `alembic upgrade head` normally for any
later revisions.

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
        "tables",
        sa.Column("id", sa.String(), primary_key=True),
        # location_id references auth's `locations` table (cross-service, same DB) — plain
        # column, not an enforced FK, since auth owns that table's migration lifecycle.
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column("pos_x", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pos_y", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("table_id", sa.String(), sa.ForeignKey("tables.id"), nullable=True),
        # discount_id references catalog's `discounts` table (cross-service) — plain column.
        sa.Column("discount_id", sa.String(), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False, server_default="dine_in"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("guest_count", sa.Integer(), nullable=True),
        sa.Column("fired_courses", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_orders_location_status", "orders", ["location_id", "status"])
    op.create_index("ix_orders_location_created", "orders", ["location_id", "created_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
        # menu_item_id references catalog's `menu_items` table (cross-service) — plain column.
        sa.Column("menu_item_id", sa.String(), nullable=False),
        sa.Column("menu_item_name", sa.String(length=255), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("modifiers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fire_course", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("guest_number", sa.Integer(), nullable=True),
        sa.Column("discount_type", sa.String(length=20), nullable=True),
        sa.Column("discount_value", sa.Float(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_comped", sa.Boolean(), nullable=False, server_default=sa.false()),
        # comped_by/created_by reference auth's `users` table (cross-service) — plain column.
        sa.Column("comped_by", sa.String(), nullable=True),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_location_created", table_name="orders")
    op.drop_index("ix_orders_location_status", table_name="orders")
    op.drop_table("orders")
    op.drop_table("tables")

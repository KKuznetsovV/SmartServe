"""baseline: create catalog-owned tables (menu_categories, menu_items, modifier_groups,
modifiers, discounts)

This is a greenfield baseline for the catalog service's first-ever Alembic chain — no
Alembic previously existed for services/catalog (see docs/microservices-plan.md / repo
notes; ordering and reporting were the first two services to get Alembic, during the
Reports feature work — catalog did NOT get one at that time despite that being a
plausible-sounding assumption, verified directly against this repo before writing this
migration). It reflects the schema these tables have had since services/catalog was
extracted, i.e. the state BEFORE the `deleted_at` column added in the next revision. Only
tables catalog owns are created here; `businesses`/`locations`/`users` are trimmed mirrors
owned by `auth` and are intentionally NOT created by this migration.

NOTE for environments where these tables already exist (e.g. a long-running dev database
whose schema predates this migration, inherited from the retired `apps/api` monolith): run
`alembic stamp 0001_baseline` instead of `alembic upgrade head` to mark this revision as
already applied without re-running the DDL, then `alembic upgrade head` normally for any
later revisions.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-20

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
        "menu_categories",
        sa.Column("id", sa.String(), primary_key=True),
        # location_id references auth's `locations` table (cross-service) — plain column.
        sa.Column("location_id", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), sa.ForeignKey("menu_categories.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_he", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("category_id", sa.String(), sa.ForeignKey("menu_categories.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_he", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_he", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("tax_rate", sa.Float(), nullable=False, server_default="0.17"),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("preparation_time_min", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_fire_course", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "modifier_groups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_he", sa.String(length=255), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_select", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "modifiers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("group_id", sa.String(), sa.ForeignKey("modifier_groups.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_he", sa.String(length=255), nullable=True),
        sa.Column("price_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "discounts",
        sa.Column("id", sa.String(), primary_key=True),
        # business_id references auth's `businesses` table (cross-service) — plain column.
        sa.Column("business_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="percent"),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("min_order_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("business_id", "code"),
    )


def downgrade() -> None:
    op.drop_table("discounts")
    op.drop_table("modifiers")
    op.drop_table("modifier_groups")
    op.drop_table("menu_items")
    op.drop_table("menu_categories")

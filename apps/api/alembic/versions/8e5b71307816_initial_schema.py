"""initial schema

Revision ID: 8e5b71307816
Revises: 
Create Date: 2026-07-31 11:37:24.636332
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '8e5b71307816'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("country", sa.String(2), nullable=False, server_default="IL"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ILS"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Jerusalem"),
        sa.Column("language", sa.String(5), nullable=False, server_default="he"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_business_id", "locations", ["business_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("pin_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="waiter"),
        sa.Column("language", sa.String(5), nullable=False, server_default="he"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_business_id", "users", ["business_id"])

    op.create_table(
        "menu_categories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_he", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_categories_location_id", "menu_categories", ["location_id"])

    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), sa.ForeignKey("menu_categories.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_he", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_he", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("tax_rate", sa.Float(), nullable=False, server_default="0.17"),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("preparation_time_min", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_items_category_id", "menu_items", ["category_id"])

    op.create_table(
        "modifier_groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_he", sa.String(255), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_select", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "modifiers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), sa.ForeignKey("modifier_groups.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_he", sa.String(255), nullable=True),
        sa.Column("price_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tables",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("pos_x", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pos_y", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tables_location_id", "tables", ["location_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("table_id", sa.String(), sa.ForeignKey("tables.id"), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False, server_default="dine_in"),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_location_status", "orders", ["location_id", "status"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("menu_item_id", sa.String(), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("menu_item_name", sa.String(255), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("modifiers", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("gateway_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "printers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="receipt"),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("port", sa.Integer(), nullable=False, server_default="9100"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "printer_routes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("printer_id", sa.String(), sa.ForeignKey("printers.id"), nullable=False),
        sa.Column("category_id", sa.String(), sa.ForeignKey("menu_categories.id"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("printer_id", "category_id"),
    )


def downgrade() -> None:
    op.drop_table("printer_routes")
    op.drop_table("printers")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("tables")
    op.drop_table("modifiers")
    op.drop_table("modifier_groups")
    op.drop_table("menu_items")
    op.drop_table("menu_categories")
    op.drop_table("users")
    op.drop_table("locations")
    op.drop_table("businesses")

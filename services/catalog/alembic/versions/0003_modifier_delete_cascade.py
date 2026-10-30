"""cascade-delete modifier groups and modifiers with their menu item

Permanently deleting a trashed item must remove catalog-owned children. Cross-service
references (order lines) still block the delete.

Revision ID: 0003_modifier_delete_cascade
Revises: 0002_menu_item_trash
Create Date: 2026-10-30

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_modifier_delete_cascade"
down_revision: str | None = "0002_menu_item_trash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("modifier_groups_item_id_fkey", "modifier_groups", type_="foreignkey")
    op.create_foreign_key(
        "modifier_groups_item_id_fkey",
        "modifier_groups",
        "menu_items",
        ["item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("modifiers_group_id_fkey", "modifiers", type_="foreignkey")
    op.create_foreign_key(
        "modifiers_group_id_fkey",
        "modifiers",
        "modifier_groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("modifiers_group_id_fkey", "modifiers", type_="foreignkey")
    op.create_foreign_key(
        "modifiers_group_id_fkey",
        "modifiers",
        "modifier_groups",
        ["group_id"],
        ["id"],
    )
    op.drop_constraint("modifier_groups_item_id_fkey", "modifier_groups", type_="foreignkey")
    op.create_foreign_key(
        "modifier_groups_item_id_fkey",
        "modifier_groups",
        "menu_items",
        ["item_id"],
        ["id"],
    )

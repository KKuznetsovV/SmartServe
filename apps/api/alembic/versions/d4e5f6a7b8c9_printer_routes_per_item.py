"""route printers per menu item instead of per category, allowing several printers per item

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-01 13:00:00.000000
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("printer_routes", sa.Column("item_id", sa.String(), sa.ForeignKey("menu_items.id"), nullable=True))
    # New rows inserted below only populate item_id; category_id must accept nulls until it's dropped
    op.alter_column("printer_routes", "category_id", nullable=True)

    # Expand each existing category-level route into one row per item currently in that category
    conn = op.get_bind()
    existing = conn.execute(sa.text("SELECT id, printer_id, category_id FROM printer_routes")).fetchall()
    for route_id, printer_id, category_id in existing:
        item_ids = conn.execute(
            sa.text("SELECT id FROM menu_items WHERE category_id = :cid"), {"cid": category_id}
        ).fetchall()
        for (item_id,) in item_ids:
            conn.execute(
                sa.text("INSERT INTO printer_routes (id, printer_id, item_id) VALUES (:id, :pid, :iid)"),
                {"id": str(uuid.uuid4()), "pid": printer_id, "iid": item_id},
            )
        conn.execute(sa.text("DELETE FROM printer_routes WHERE id = :id"), {"id": route_id})

    op.drop_constraint("printer_routes_printer_id_category_id_key", "printer_routes", type_="unique")
    op.drop_column("printer_routes", "category_id")
    op.alter_column("printer_routes", "item_id", nullable=False)
    op.create_unique_constraint("printer_routes_printer_id_item_id_key", "printer_routes", ["printer_id", "item_id"])


def downgrade() -> None:
    op.add_column(
        "printer_routes", sa.Column("category_id", sa.String(), sa.ForeignKey("menu_categories.id"), nullable=True)
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE printer_routes SET category_id = "
            "(SELECT category_id FROM menu_items WHERE menu_items.id = printer_routes.item_id)"
        )
    )
    op.drop_constraint("printer_routes_printer_id_item_id_key", "printer_routes", type_="unique")
    op.drop_column("printer_routes", "item_id")
    op.alter_column("printer_routes", "category_id", nullable=False)
    op.create_unique_constraint(
        "printer_routes_printer_id_category_id_key", "printer_routes", ["printer_id", "category_id"]
    )

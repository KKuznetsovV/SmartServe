"""add parent_id to menu_categories, enabling subcategories

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-01 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "menu_categories", sa.Column("parent_id", sa.String(), sa.ForeignKey("menu_categories.id"), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("menu_categories", "parent_id")

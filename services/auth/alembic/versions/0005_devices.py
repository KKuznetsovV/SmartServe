"""paired POS/KDS/display devices with hashed tokens

Revision ID: 0005_devices
Revises: 0004_vat_rate
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_devices"
down_revision: str | None = "0004_vat_rate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_devices_token_hash", "devices", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_devices_token_hash", table_name="devices")
    op.drop_table("devices")

"""business and location VAT rates (inclusive shelf prices)

Menu prices are VAT-inclusive shelf prices. Existing catalog prices are not converted:
they are already the amounts guests see.

Revision ID: 0004_vat_rate
Revises: 0003_outbox
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_vat_rate"
down_revision: str | None = "0003_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("vat_rate", sa.Numeric(5, 4), nullable=False, server_default="0.18"),
    )
    op.add_column("locations", sa.Column("vat_rate", sa.Numeric(5, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("locations", "vat_rate")
    op.drop_column("businesses", "vat_rate")

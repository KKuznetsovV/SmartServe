"""lowercase existing emails and unique-index lower(email)

Revision ID: 0002_lowercase_email_unique
Revises: 0001_baseline
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_lowercase_email_unique"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    duplicates = (
        conn.execute(
            sa.text(
                """
            SELECT lower(email) AS email, count(*) AS n
            FROM users
            WHERE email IS NOT NULL
            GROUP BY lower(email)
            HAVING count(*) > 1
            """
            )
        )
        .mappings()
        .all()
    )
    if duplicates:
        listing = ", ".join(f"{row['email']} x{row['n']}" for row in duplicates)
        raise RuntimeError(f"Cannot lowercase emails; duplicate addresses: {listing}")

    op.execute(sa.text("UPDATE users SET email = lower(email) WHERE email IS NOT NULL"))
    op.execute(sa.text("CREATE UNIQUE INDEX ix_users_email_lower ON users (lower(email))"))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email_lower"))

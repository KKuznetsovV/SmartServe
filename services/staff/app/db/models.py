"""SQLAlchemy ORM models — staff service owns Shift; mutates the shared users table for
staff CRUD (User is a trimmed, read-only-elsewhere mirror of the table owned by `auth` —
same physical Postgres instance, schema-per-service mapping only, see
docs/microservices-plan.md §4). Shift.location_id is a plain string (not a ForeignKey)
since Location isn't needed/mirrored here — shifts only ever look it up by value, never
traverse a relationship to it.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─── User (owned by auth, trimmed mirror) ─────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="waiter")
    language: Mapped[str] = mapped_column(String(5), default="he")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ─── Shifts (owned here) ───────────────────────────────────────────────────────


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    opened_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opening_cash: Mapped[float] = mapped_column(Float, default=0.0)
    closing_cash: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="open")
    notes: Mapped[str | None] = mapped_column(Text)

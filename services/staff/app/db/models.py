"""SQLAlchemy ORM models — staff service owns Shift.

User and Location are trimmed read-only mirrors of tables owned by `auth`
(see docs/microservices-plan.md §4). Staff CRUD lives on auth.
"""

import uuid
from datetime import UTC, datetime

from smartserve_shared.mirrors import ReadOnlyMirror
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─── User (owned by auth, trimmed mirror) ─────────────────────────────────────


class User(ReadOnlyMirror, Base):
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


# ─── Location (owned by auth, trimmed mirror) ─────────────────────────────────


class Location(ReadOnlyMirror, Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


# ─── Shifts (owned here) ───────────────────────────────────────────────────────


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    opened_by: Mapped[str] = mapped_column(String(), nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opening_cash: Mapped[float] = mapped_column(Float, default=0.0)
    closing_cash: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="open")
    notes: Mapped[str | None] = mapped_column(Text)

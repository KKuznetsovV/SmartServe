"""SQLAlchemy ORM models — payments service owns Payment.

`User` is a trimmed, read-only mirror of the table owned by `auth`; `Order` is a
trimmed, read-only mirror of the table owned by `ordering` — same physical Postgres
instance, schema-per-service mapping only (see docs/microservices-plan.md §4).
Payment endpoints here are role-scoped only (no business/location checks), so
`Order` is trimmed to just the fields PaymentService reads/writes (status, total) —
location/table/discount linkage isn't needed and is intentionally omitted.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


# ─── Order (owned by ordering, trimmed mirror) ────────────────────────────────


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(50), default="open")
    total: Mapped[float] = mapped_column(Float, default=0.0)

    payments: Mapped[list[Payment]] = relationship(back_populates="order")


# ─── Payments (owned here) ────────────────────────────────────────────────────


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    tip_amount: Mapped[float] = mapped_column(Float, default=0.0)
    guest_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    gateway_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped[Order] = relationship(back_populates="payments")

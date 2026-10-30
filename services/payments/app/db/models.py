"""SQLAlchemy ORM models — payments service owns Payment.

`User` is a trimmed, read-only mirror of the table owned by `auth`; `Order` is a
trimmed, read-only mirror of the table owned by `ordering` — same physical Postgres
instance, schema-per-service mapping only (see docs/microservices-plan.md §4).
`Order` is trimmed to the fields PaymentService reads (status, total, location_id)
so tenant checks can resolve the order's location without mirroring the rest of ordering.
Payments never writes `orders` — fully-paid is computed from payment rows plus `Order.total`.
"""

import uuid
from datetime import UTC, datetime

from smartserve_shared.mirrors import ReadOnlyMirror
from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


# ─── Order (owned by ordering, trimmed mirror) ────────────────────────────────


class Order(ReadOnlyMirror, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open")
    total: Mapped[float] = mapped_column(Float, default=0.0)

    payments: Mapped[list[Payment]] = relationship(
        back_populates="order",
        primaryjoin="Payment.order_id == Order.id",
        foreign_keys="[Payment.order_id]",
    )


# ─── Payments (owned here) ────────────────────────────────────────────────────


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    tip_amount: Mapped[float] = mapped_column(Float, default=0.0)
    guest_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    gateway_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped[Order] = relationship(
        back_populates="payments",
        primaryjoin="Payment.order_id == Order.id",
        foreign_keys=[order_id],
    )

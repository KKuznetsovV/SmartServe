"""SQLAlchemy ORM models — reporting service owns denormalized reads over Order +
OrderItem, trimmed to just the columns the summary aggregation queries need. User is a
trimmed, read-only-elsewhere mirror (see docs/microservices-plan.md §4). Order.location_id
is a plain string (not a ForeignKey) since Location (auth) isn't mirrored here — reports
only filters by the id value, never joins to it. OrderItem.order_id stays a real
ForeignKey to the locally-mirrored orders.id (needed for the join in the top-items
query); menu_item_id isn't mirrored at all since only the denormalized menu_item_name
snapshot column is read.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
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


# ─── Orders (owned by ordering, trimmed read-only mirror for aggregation) ──────


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="dine_in")
    status: Mapped[str] = mapped_column(String(50), default="open")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)


# ─── Event log (owned here) ────────────────────────────────────────────────────


class EventLog(Base):
    """Generic audit trail of every RabbitMQ event received on the `smartserve.events`
    topic exchange (wildcard `#` subscription) — see docs/microservices-plan.md §4."""

    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(String(), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

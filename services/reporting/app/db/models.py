"""SQLAlchemy ORM models — reporting service owns denormalized reads over Order +
OrderItem, trimmed to just the columns the summary/report aggregation queries need. User
and Location are trimmed, read-only-elsewhere mirrors (see docs/microservices-plan.md §4).
Order.location_id is a plain string (not a ForeignKey to the local Location mirror) since
reports only filter by the id value, never join to it — the Location mirror exists purely
so `GET .../reports/*` endpoints can verify a `location_id` path param actually belongs to
the caller's own business before running any query (see `verify_location_owned` in
smartserve_shared.tenancy). OrderItem.order_id stays a real ForeignKey to the
locally-mirrored orders.id (needed for the join in the top-items/category/server queries).

Reporting's own Alembic chain (see alembic/) only ever creates/alters `event_log` — the
Order/OrderItem/User/Location classes below are read-only mappings onto tables owned and
migrated by `ordering`/`auth` and must never be given their own DDL here.
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


# ─── User / Location (owned by auth, trimmed mirror) ──────────────────────────


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


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


# ─── Orders (owned by ordering, trimmed read-only mirror for aggregation) ──────


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(String(), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="dine_in")
    status: Mapped[str] = mapped_column(String(50), default="open")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[str | None] = mapped_column(String(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    menu_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(), nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
